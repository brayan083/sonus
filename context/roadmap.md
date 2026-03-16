# Roadmap

## Implemented Features

- **Transcription**: Upload audio/video, transcribe with local Whisper models or OpenAI API, real-time progress, cancellation, download as JSON/TXT/SRT
- **History**: List, rename, delete transcriptions
- **Summarization**: Single or multi-transcription summaries with 4 types (general, class notes, study guide, combined), 3 lengths, configurable language
- **Summary History**: List, rename, delete summaries
- **Settings**: Whisper model/language, AI provider (Ollama/Gemini), API keys, model selection
- **Theme**: Dark/light mode with localStorage persistence
- **Active Jobs**: Indicator showing running transcriptions

## Planned / Stub Features

- **Chat**: `placeholder.html` exists but no chat route is implemented yet. Intended for conversational interaction with transcriptions.
- **More AI providers**: Currently Ollama and Gemini. OpenAI GPT could be added as a summarization provider.

## Potential Improvements

- Persistent job tracking (survives server restart) — currently in-memory only
- WebSocket for real-time progress instead of polling
- User authentication
- Batch transcription (upload multiple files at once)
- Search across transcriptions
- Export summaries as PDF
- Speaker diarization
- Audio player synced with transcript segments
