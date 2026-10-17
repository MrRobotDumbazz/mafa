from dataclasses import dataclass, field


@dataclass
class Evidence:
    timestamp_sec: float
    frame: str | None = None


@dataclass
class MLNormative:
    document: str | None = None
    clause: str | None = None
    url: str | None = None


@dataclass
class MLEvent:
    type: str
    timecode_sec: float
    description: str
    evidence: list[Evidence] = field(default_factory=list)
    timecode_end_sec: float | None = None
    confidence: float | None = None
    normative: MLNormative | None = None


@dataclass
class MLResult:
    video_id: str
    pipeline_version: str
    events: list[MLEvent] = field(default_factory=list)
