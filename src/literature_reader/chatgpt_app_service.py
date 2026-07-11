"""Ephemeral job storage for the ChatGPT App / MCP integration.

This module deliberately does *not* call an LLM or require an OpenAI API key.
ChatGPT supplies the reading intelligence in the conversation; this service keeps
the uploaded source, validates the source-to-note anchors, and renders the final
HTML/DOCX files.
"""

from __future__ import annotations

import re
import secrets
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import RunConfig
from .extractors import SUPPORTED_SUFFIXES, extract_document
from .models import Annotation, PaperMap, ReadingCopy, SourceDocument
from .pipeline import write_outputs
from .quality import validate_reading_copy


class ReadingJobError(ValueError):
    """Raised when an MCP reading-copy operation cannot be completed safely."""


@dataclass
class ReadingJob:
    """One short-lived uploaded document and its model-supplied annotations."""

    job_id: str
    directory: Path
    source: SourceDocument
    translation: str
    created_at: datetime
    paper_map: PaperMap | None = None
    annotations: dict[str, Annotation] = field(default_factory=dict)
    rendered_files: dict[str, Path] = field(default_factory=dict)


class ReadingJobStore:
    """Keep uploads only long enough to finish and download a reading copy.

    The initial App implementation is intentionally single-process and designed
    for a developer's private ChatGPT connection. A public multi-user service
    should replace this in-memory store with authenticated durable storage.
    """

    def __init__(
        self,
        root_directory: str | Path,
        *,
        ttl_minutes: int = 60,
        batch_size: int = 4,
    ) -> None:
        if ttl_minutes < 1:
            raise ValueError("ttl_minutes must be at least 1.")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")
        self.root_directory = Path(root_directory).expanduser().resolve()
        self.root_directory.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(minutes=ttl_minutes)
        self.batch_size = batch_size
        self._jobs: dict[str, ReadingJob] = {}
        self._lock = threading.RLock()
        self._cleanup_orphaned_directories()

    def create_from_bytes(
        self,
        *,
        filename: str | None,
        content: bytes,
        translation: str,
    ) -> dict[str, Any]:
        """Create a job from an already-authorized ChatGPT file download."""

        if translation not in {"none", "full"}:
            raise ReadingJobError("translation must be 'none' or 'full'.")
        if not content:
            raise ReadingJobError("The uploaded file is empty.")

        safe_filename = _safe_upload_name(filename)
        with self._lock:
            self.cleanup_expired()
            job_id = secrets.token_urlsafe(20)
            directory = self.root_directory / job_id
            directory.mkdir(parents=True, exist_ok=False)
            source_path = directory / safe_filename
            try:
                source_path.write_bytes(content)
                source = extract_document(source_path)
            except Exception:
                shutil.rmtree(directory, ignore_errors=True)
                raise

            job = ReadingJob(
                job_id=job_id,
                directory=directory,
                source=source,
                translation=translation,
                created_at=_utcnow(),
            )
            self._jobs[job_id] = job
            return self._job_start_payload(job)

    def document_outline(self, job_id: str) -> dict[str, Any]:
        """Return a compact outline so ChatGPT can form a paper-level map."""

        with self._lock:
            job = self._require_job(job_id)
            sections: list[dict[str, Any]] = []
            current: dict[str, Any] | None = None
            for paragraph in job.source.paragraphs:
                section_name = paragraph.section or "未标记章节"
                if current is None or current["section"] != section_name:
                    current = {
                        "section": section_name,
                        "first_anchor": paragraph.anchor,
                        "last_anchor": paragraph.anchor,
                        "paragraph_count": 0,
                        "preview": _preview(paragraph.text),
                    }
                    sections.append(current)
                current["last_anchor"] = paragraph.anchor
                current["paragraph_count"] += 1

            return {
                "job_id": job.job_id,
                "title": job.source.title,
                "paragraph_count": len(job.source.paragraphs),
                "batch_count": self._batch_count(job),
                "sections": sections,
                "instruction": (
                    "请结合已上传的原文，先形成中文论文阅读地图；随后调用 "
                    "save_paper_map 保存它。不要把章节标题当作正文段落批注。"
                ),
            }

    def annotation_batch(self, job_id: str, batch_index: int) -> dict[str, Any]:
        """Return a small source-aligned batch with immediate context."""

        with self._lock:
            job = self._require_job(job_id)
            total_batches = self._batch_count(job)
            if batch_index < 0 or batch_index >= total_batches:
                raise ReadingJobError(
                    f"batch_index must be between 0 and {max(total_batches - 1, 0)}."
                )
            start = batch_index * self.batch_size
            batch = job.source.paragraphs[start : start + self.batch_size]
            previous = job.source.paragraphs[start - 1] if start else None
            following_index = start + len(batch)
            following = (
                job.source.paragraphs[following_index]
                if following_index < len(job.source.paragraphs)
                else None
            )
            return {
                "job_id": job.job_id,
                "batch_index": batch_index,
                "batch_count": total_batches,
                "previous_context": _paragraph_payload(previous) if previous else None,
                "following_context": _paragraph_payload(following) if following else None,
                "paragraphs": [_paragraph_payload(paragraph) for paragraph in batch],
                "instruction": _annotation_instruction(job.translation),
            }

    def save_paper_map(
        self,
        job_id: str,
        *,
        research_question: str,
        central_claim: str,
        argument_map: Sequence[str],
        scope_notes: str,
    ) -> dict[str, Any]:
        """Persist the map composed by ChatGPT from the uploaded paper."""

        with self._lock:
            job = self._require_job(job_id)
            values = {
                "research_question": research_question,
                "central_claim": central_claim,
                "scope_notes": scope_notes,
            }
            empty = [name for name, value in values.items() if not value.strip()]
            cleaned_argument_map = tuple(item.strip() for item in argument_map if item.strip())
            if empty or not cleaned_argument_map:
                missing = ", ".join([*empty, *( ["argument_map"] if not cleaned_argument_map else [])])
                raise ReadingJobError(f"Paper map fields cannot be empty: {missing}.")

            job.paper_map = PaperMap(
                title=job.source.title,
                research_question=research_question.strip(),
                central_claim=central_claim.strip(),
                argument_map=cleaned_argument_map,
                scope_notes=scope_notes.strip(),
            )
            return {
                "job_id": job.job_id,
                "status": "paper_map_saved",
                "next_step": "Call get_annotation_batch for batch_index 0, then save_annotation_batch.",
            }

    def save_annotations(
        self,
        job_id: str,
        annotations: Sequence[Mapping[str, object]],
    ) -> dict[str, Any]:
        """Validate and store one batch of model-written source-linked notes."""

        with self._lock:
            job = self._require_job(job_id)
            expected = {paragraph.anchor for paragraph in job.source.paragraphs}
            saved: list[str] = []
            seen: set[str] = set()
            for item in annotations:
                annotation = _annotation_from_payload(item, job.translation)
                if annotation.anchor not in expected:
                    raise ReadingJobError(f"Unknown paragraph anchor: {annotation.anchor}.")
                if annotation.anchor in seen:
                    raise ReadingJobError(f"Duplicate paragraph anchor in this batch: {annotation.anchor}.")
                seen.add(annotation.anchor)
                job.annotations[annotation.anchor] = annotation
                saved.append(annotation.anchor)

            if not saved:
                raise ReadingJobError("Provide at least one paragraph annotation.")
            progress = self._progress_payload(job)
            return {
                "job_id": job.job_id,
                "saved_anchors": saved,
                **progress,
                "next_step": _next_annotation_step(progress),
            }

    def progress(self, job_id: str) -> dict[str, Any]:
        """Report what still needs to be annotated before rendering."""

        with self._lock:
            return {"job_id": job_id, **self._progress_payload(self._require_job(job_id))}

    def render(self, job_id: str, output_format: str) -> dict[str, Path]:
        """Render the fully validated reading copy and remember safe download paths."""

        with self._lock:
            job = self._require_job(job_id)
            if output_format not in {"html", "docx", "all"}:
                raise ReadingJobError("output_format must be 'html', 'docx', or 'all'.")
            reading_copy = self._reading_copy(job)
            output_paths = write_outputs(reading_copy, job.directory / "output", output_format)
            rendered = {
                key: path
                for key, path in {"html": output_paths.html, "docx": output_paths.docx}.items()
                if path is not None
            }
            job.rendered_files.update(rendered)
            return rendered

    def download_path(self, job_id: str, filename: str) -> Path:
        """Resolve a generated file without allowing arbitrary path access."""

        with self._lock:
            job = self._require_job(job_id)
            requested = Path(filename).name
            for path in job.rendered_files.values():
                if path.name == requested and path.exists():
                    return path
            raise ReadingJobError("The requested output file is unavailable or has expired.")

    def cleanup_expired(self) -> int:
        """Delete stale local uploads and generated files; return number of jobs removed."""

        with self._lock:
            now = _utcnow()
            expired_ids = [
                job_id
                for job_id, job in self._jobs.items()
                if now - job.created_at >= self.ttl
            ]
            for job_id in expired_ids:
                job = self._jobs.pop(job_id)
                shutil.rmtree(job.directory, ignore_errors=True)
            return len(expired_ids) + self._cleanup_orphaned_directories(now)

    def clear_all(self) -> int:
        """Remove all jobs created by this process, for normal server shutdown."""

        with self._lock:
            jobs = list(self._jobs.values())
            self._jobs.clear()
            for job in jobs:
                shutil.rmtree(job.directory, ignore_errors=True)
            return len(jobs)

    def _require_job(self, job_id: str) -> ReadingJob:
        self.cleanup_expired()
        job = self._jobs.get(job_id)
        if job is None:
            raise ReadingJobError("This reading job is unavailable or has expired. Upload the paper again.")
        return job

    def _batch_count(self, job: ReadingJob) -> int:
        return (len(job.source.paragraphs) + self.batch_size - 1) // self.batch_size

    def _job_start_payload(self, job: ReadingJob) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "title": job.source.title,
            "paragraph_count": len(job.source.paragraphs),
            "batch_count": self._batch_count(job),
            "translation": job.translation,
            "expires_in_minutes": int(self.ttl.total_seconds() // 60),
            "workflow": [
                "Call get_document_outline and save_paper_map.",
                "For every batch index, call get_annotation_batch and then save_annotation_batch.",
                "Call get_reading_progress. Only when it is complete, call render_reading_copy.",
            ],
        }

    def _progress_payload(self, job: ReadingJob) -> dict[str, Any]:
        expected = [paragraph.anchor for paragraph in job.source.paragraphs]
        missing = [anchor for anchor in expected if anchor not in job.annotations]
        return {
            "paper_map_saved": job.paper_map is not None,
            "annotated_paragraph_count": len(job.annotations),
            "total_paragraph_count": len(expected),
            "missing_anchors": missing,
            "complete": job.paper_map is not None and not missing,
        }

    def _reading_copy(self, job: ReadingJob) -> ReadingCopy:
        if job.paper_map is None:
            raise ReadingJobError("Save the paper map before rendering the reading copy.")
        expected = [paragraph.anchor for paragraph in job.source.paragraphs]
        missing = [anchor for anchor in expected if anchor not in job.annotations]
        if missing:
            preview = ", ".join(missing[:12])
            suffix = " …" if len(missing) > 12 else ""
            raise ReadingJobError(
                f"Cannot render yet. Missing annotations for: {preview}{suffix}"
            )
        annotations = tuple(job.annotations[anchor] for anchor in expected)
        reading_copy = ReadingCopy(
            source=job.source,
            paper_map=job.paper_map,
            annotations=annotations,
        )
        try:
            warnings = validate_reading_copy(
                reading_copy,
                RunConfig(provider="mock", translation=job.translation),
            )
        except ValueError as error:
            raise ReadingJobError(str(error)) from error
        return ReadingCopy(
            source=reading_copy.source,
            paper_map=reading_copy.paper_map,
            annotations=reading_copy.annotations,
            warnings=warnings,
        )

    def _cleanup_orphaned_directories(self, now: datetime | None = None) -> int:
        """Remove directories left by a prior crashed process after their TTL."""

        now = now or _utcnow()
        removed = 0
        active_directories = {job.directory for job in self._jobs.values()}
        for candidate in self.root_directory.iterdir():
            if not candidate.is_dir() or candidate in active_directories:
                continue
            modified_at = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
            if now - modified_at >= self.ttl:
                shutil.rmtree(candidate, ignore_errors=True)
                removed += 1
        return removed


def _annotation_from_payload(
    payload: Mapping[str, object],
    translation_mode: str,
) -> Annotation:
    fields = ("anchor", "role", "context", "explanation", "takeaway", "caveat")
    values: dict[str, str] = {}
    for field_name in fields:
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ReadingJobError(f"Annotation field '{field_name}' cannot be empty.")
        values[field_name] = value.strip()
    translation_value = payload.get("translation")
    translation = translation_value.strip() if isinstance(translation_value, str) else None
    if translation_mode == "full" and not translation:
        raise ReadingJobError("Full translation was requested, but an annotation has no translation.")
    return Annotation(
        anchor=values["anchor"],
        role=values["role"],
        context=values["context"],
        explanation=values["explanation"],
        takeaway=values["takeaway"],
        caveat=values["caveat"],
        translation=translation,
    )


def _annotation_instruction(translation: str) -> str:
    translation_instruction = (
        "同时为每个段落给出忠实的中文全文翻译。"
        if translation == "full"
        else "不要给出全文翻译。"
    )
    return (
        "为返回的每个锚点写一条中文批注，然后调用 save_annotation_batch。"
        "批注必须解释该段在整篇论文论证中的作用，并明确与前后段的关系；"
        "不要只复述或逐句翻译原文。保留必要的英文术语、变量名和原文事实边界。"
        + translation_instruction
    )


def _next_annotation_step(progress: Mapping[str, object]) -> str:
    if progress["complete"]:
        return "All anchors are complete. Call render_reading_copy to generate the download files."
    missing = progress["missing_anchors"]
    if isinstance(missing, list) and missing:
        return "Call get_annotation_batch for the batch that contains the next missing anchor."
    return "Call get_reading_progress before rendering."


def _paragraph_payload(paragraph) -> dict[str, Any]:
    return {
        "anchor": paragraph.anchor,
        "section": paragraph.section,
        "page_number": paragraph.page_number,
        "text": paragraph.text,
    }


def _safe_upload_name(filename: str | None) -> str:
    candidate = Path(filename or "paper.pdf").name.strip() or "paper.pdf"
    suffix = Path(candidate).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ReadingJobError(f"Unsupported file type '{suffix or 'unknown'}'. Supported types: {allowed}.")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(candidate).stem).strip("._") or "paper"
    return f"{stem[:120]}{suffix}"


def _preview(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[:limit - 1]}…"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
