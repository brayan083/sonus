"""AI service — Ollama + Gemini inference."""

import requests

# ── Prompt templates ─────────────────────────────────────

SUMMARY_TYPES = {
    "general":       "Resumen general",
    "class_notes":   "Apuntes de clase",
    "study_guide":   "Guía de estudio",
    "combined":      "Combinado (resumen + apuntes + guía)",
}

SUMMARY_LENGTHS = {
    "short":    "Sé conciso pero desarrolla las ideas en oraciones completas. Máximo 2-3 párrafos.",
    "medium":   "Desarrolla cada idea con explicaciones claras. No te limites en extensión — incluye todo lo necesario para cubrir cada tema completamente.",
    "detailed": "Sé exhaustivo y completo. Desarrolla CADA tema en profundidad con párrafos bien estructurados, explicando conceptos, incluyendo ejemplos y dando contexto. No te preocupes por la extensión — es mucho más importante no omitir ningún tema o detalle que ser breve.",
}

_STYLE_GUIDE = (
    "\n\nIMPORTANTE sobre el formato de tu respuesta:\n"
    "- Usa encabezados con ## para secciones principales y ### para subsecciones.\n"
    "- Desarrolla las ideas en PÁRRAFOS completos y bien redactados, NO uses listas con viñetas como formato principal.\n"
    "- Las listas con viñetas (-) solo deben usarse para enumerar elementos cortos (ej: nombres, fechas, requisitos concretos), nunca para explicar conceptos.\n"
    "- Cada sección debe tener al menos un párrafo explicativo antes de cualquier lista.\n"
    "- Escribe de forma fluida y natural, como un artículo bien estructurado, no como apuntes telegráficos."
)

_PROMPTS = {
    "general": (
        "Genera un resumen claro, coherente y bien redactado del siguiente contenido transcrito. "
        "Organiza el contenido en secciones temáticas con encabezados. Desarrolla cada tema en párrafos "
        "completos que expliquen las ideas, no solo las enumeren."
    ),
    "class_notes": (
        "Genera apuntes de clase completos y bien organizados a partir del siguiente contenido transcrito. "
        "Organiza por temas y subtemas con encabezados. Para cada tema, explica los conceptos con definiciones claras, "
        "incluye los ejemplos que se mencionaron en clase, y destaca las relaciones entre conceptos. "
        "Si se mencionan fórmulas, reglas o pasos, preséntalos de forma clara. "
        "El objetivo es que estos apuntes sirvan para estudiar y repasar la materia."
    ),
    "study_guide": (
        "Genera una guía de estudio a partir del siguiente contenido transcrito. Estructura el documento así:\n"
        "## Resumen del tema\nUn párrafo con la visión general de lo que se trató.\n"
        "## Conceptos clave\nExplica cada concepto importante con definiciones y ejemplos.\n"
        "## Puntos importantes para recordar\nLos aspectos más relevantes que hay que memorizar o entender bien.\n"
        "## Preguntas de repaso\nFormula 5-8 preguntas que ayuden a verificar la comprensión del tema."
    ),
    "combined": (
        "Del siguiente contenido transcrito genera un documento completo con las siguientes secciones:\n"
        "## Resumen General\nUn resumen de 2-3 párrafos con las ideas principales.\n"
        "## Desarrollo Temático\nDesarrolla cada tema tratado en subsecciones (###) con párrafos explicativos, "
        "definiciones y ejemplos.\n"
        "## Guía de estudio\nConceptos clave para recordar y preguntas de repaso."
    ),
}

GEMINI_MODELS = {
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite (más rápido, más barato)",
    "gemini-2.5-flash": "Gemini 2.5 Flash (rápido, buena calidad)",
    "gemini-2.5-pro": "Gemini 2.5 Pro (máxima calidad)",
}

CHUNK_WORD_THRESHOLD = 8000  # words — above this, use chunked summarization
CHUNK_TARGET_WORDS = 5000    # target words per chunk


def build_multi_prompt(summary_type: str, length: str, language: str,
                       transcriptions: list[dict]) -> str:
    """Build a prompt for summarizing multiple transcriptions in order."""
    instruction = _PROMPTS.get(summary_type, _PROMPTS["general"])
    length_hint = SUMMARY_LENGTHS.get(length, SUMMARY_LENGTHS["medium"])
    lang_name = {"es": "español", "en": "inglés", "fr": "francés", "de": "alemán",
                 "pt": "portugués", "it": "italiano", "ja": "japonés", "zh": "chino",
                 "ko": "coreano", "ru": "ruso", "ar": "árabe"}.get(language, language)

    parts = []
    for i, t in enumerate(transcriptions, 1):
        text = " ".join(seg["text"] for seg in t.get("segments", []))
        parts.append(f"--- PARTE {i}: {t.get('filename', '?')} ---\n{text}")

    joined = "\n\n".join(parts)
    return (
        f"{instruction}\n\n"
        f"A continuación se presentan {len(transcriptions)} transcripciones en orden secuencial "
        f"(pueden ser partes de una misma clase o sesión). "
        f"Genera un resumen unificado que integre toda la información en orden.\n\n"
        f"{length_hint}\n"
        f"Responde en {lang_name}."
        f"{_STYLE_GUIDE}\n\n"
        f"{joined}\n--- FIN ---"
    )


def build_prompt(summary_type: str, length: str, language: str, text: str,
                 attachments_text: str = "") -> str:
    instruction = _PROMPTS.get(summary_type, _PROMPTS["general"])
    length_hint = SUMMARY_LENGTHS.get(length, SUMMARY_LENGTHS["medium"])
    lang_name = {"es": "español", "en": "inglés", "fr": "francés", "de": "alemán",
                 "pt": "portugués", "it": "italiano", "ja": "japonés", "zh": "chino",
                 "ko": "coreano", "ru": "ruso", "ar": "árabe"}.get(language, language)

    context_section = ""
    if attachments_text:
        context_section = (
            "A continuación se incluye material de apoyo (PDFs, presentaciones, etc.) "
            "que complementa la transcripción. Úsalo para enriquecer y dar más contexto al resumen.\n\n"
            f"--- CONTEXTO ADICIONAL ---\n{attachments_text}\n--- FIN CONTEXTO ---\n\n"
        )

    return (
        f"{instruction}\n\n"
        f"{length_hint}\n"
        f"Responde en {lang_name}."
        f"{_STYLE_GUIDE}\n\n"
        f"{context_section}"
        f"--- TRANSCRIPCIÓN ---\n{text}\n--- FIN ---"
    )


# ── Chunked summarization ──────────────────────────────

def _split_into_chunks(text: str, target_words: int = CHUNK_TARGET_WORDS) -> list[str]:
    """Split text into chunks of roughly target_words size, breaking at sentence boundaries."""
    words = text.split()
    if len(words) <= target_words:
        return [text]

    chunks = []
    sentences = text.replace(".\n", ". \n").split(". ")
    current = []
    current_len = 0

    for sent in sentences:
        sent_words = len(sent.split())
        if current_len + sent_words > target_words and current:
            chunks.append(". ".join(current) + ".")
            current = [sent]
            current_len = sent_words
        else:
            current.append(sent)
            current_len += sent_words

    if current:
        chunks.append(". ".join(current))

    return chunks


def _build_chunk_extract_prompt(chunk_text: str, chunk_num: int, total_chunks: int,
                                language: str) -> str:
    lang_name = {"es": "español", "en": "inglés"}.get(language, language)
    return (
        f"Eres un asistente que extrae información de transcripciones de clase.\n\n"
        f"Esta es la parte {chunk_num} de {total_chunks} de una transcripción.\n"
        f"Extrae TODOS los temas, conceptos, definiciones, ejemplos, fórmulas, "
        f"datos importantes y cualquier información relevante. No omitas nada.\n"
        f"Organiza la información por temas con encabezados.\n"
        f"Responde en {lang_name}.\n\n"
        f"--- FRAGMENTO {chunk_num}/{total_chunks} ---\n{chunk_text}\n--- FIN ---"
    )


def _build_final_integration_prompt(chunk_summaries: list[str], summary_type: str,
                                     length: str, language: str,
                                     attachments_text: str = "") -> str:
    instruction = _PROMPTS.get(summary_type, _PROMPTS["general"])
    length_hint = SUMMARY_LENGTHS.get(length, SUMMARY_LENGTHS["medium"])
    lang_name = {"es": "español", "en": "inglés", "fr": "francés", "de": "alemán",
                 "pt": "portugués", "it": "italiano", "ja": "japonés", "zh": "chino",
                 "ko": "coreano", "ru": "ruso", "ar": "árabe"}.get(language, language)

    parts = []
    for i, s in enumerate(chunk_summaries, 1):
        parts.append(f"--- PARTE {i}/{len(chunk_summaries)} ---\n{s}")
    joined = "\n\n".join(parts)

    context_section = ""
    if attachments_text:
        context_section = (
            "También se incluye material de apoyo (PDFs, presentaciones, etc.) "
            "que complementa la transcripción. Úsalo para enriquecer el resumen.\n\n"
            f"--- CONTEXTO ADICIONAL ---\n{attachments_text}\n--- FIN CONTEXTO ---\n\n"
        )

    return (
        f"{instruction}\n\n"
        f"A continuación tienes la información extraída de una transcripción larga, "
        f"dividida en {len(chunk_summaries)} partes secuenciales. "
        f"Genera un documento COMPLETO e INTEGRADO que cubra TODA la información sin perder ningún tema.\n"
        f"IMPORTANTE: No te limites en extensión. El documento puede ser tan largo como sea necesario. "
        f"Es MUCHO más importante incluir toda la información que ser breve. "
        f"Si un tema se trató en detalle, desarróllalo en detalle.\n\n"
        f"{length_hint}\n"
        f"Responde en {lang_name}."
        f"{_STYLE_GUIDE}\n\n"
        f"{context_section}"
        f"{joined}\n--- FIN ---"
    )


def needs_chunking(text: str, attachments_text: str = "") -> bool:
    """Check if the combined text exceeds the chunking threshold."""
    total_words = len(text.split()) + len(attachments_text.split())
    return total_words > CHUNK_WORD_THRESHOLD


def summarize_chunked(text: str, summary_type: str, length: str, language: str,
                      cfg: dict, attachments_text: str = "",
                      on_progress=None) -> str:
    """Summarize long text by chunking, extracting from each chunk, then integrating."""
    chunks = _split_into_chunks(text)
    total = len(chunks)

    if on_progress:
        on_progress(f"Dividido en {total} fragmentos, procesando...")

    chunk_summaries = []
    for i, chunk in enumerate(chunks, 1):
        if on_progress:
            on_progress(f"Procesando fragmento {i}/{total}...")
        prompt = _build_chunk_extract_prompt(chunk, i, total, language)
        result = summarize(prompt, cfg)
        chunk_summaries.append(result)

    if on_progress:
        on_progress("Integrando resumen final...")

    final_prompt = _build_final_integration_prompt(
        chunk_summaries, summary_type, length, language, attachments_text
    )
    return summarize(final_prompt, cfg)


# ── Ollama provider ─────────────────────────────────────

def summarize_ollama(prompt: str, base_url: str = "http://localhost:11434", model: str = "llama3.2") -> str:
    r = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["response"]


# ── Gemini provider ─────────────────────────────────────

def summarize_gemini(prompt: str, api_key: str, model: str = "gemini-2.5-pro") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = requests.post(
        url,
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 65536},
        },
        timeout=600,
    )
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Unified summarize ───────────────────────────────────

def summarize(prompt: str, cfg: dict) -> str:
    """Summarize using the configured provider."""
    provider = cfg.get("ai_provider", "ollama")
    if provider == "gemini":
        api_key = cfg.get("gemini_api_key", "")
        if not api_key:
            raise ValueError("Gemini API key no configurada. Ve a Configuración.")
        return summarize_gemini(prompt, api_key, cfg.get("gemini_model", "gemini-2.5-pro"))
    return summarize_ollama(
        prompt,
        base_url=cfg.get("ollama_url", "http://localhost:11434"),
        model=cfg.get("ollama_model", "llama3.2"),
    )
