# Sonus

Flask web application that transcribes audio and video files using Whisper and generates AI-powered summaries. Designed for processing lectures, meetings, and educational content into transcripts and study materials.

## Screenshots

| Transcription | Real-time |
|:---:|:---:|
| ![Transcribe](img%20readme/image%201.png) | ![Real-time](img%20readme/image%202.png) |

| History | Summary |
|:---:|:---:|
| ![History](img%20readme/image%203.png) | ![Summary](img%20readme/image%204.png) |

## Features

### Transcription
- **Multiple formats**: MP4, MP3, M4A, WAV, MOV, MKV, WEBM
- **Two engines**: Local (`faster-whisper`) with real-time progress or OpenAI Whisper API (auto-splits files >24MB)
- **Model selection**: tiny, base, small, medium, large, large-v2, large-v3, large-v3-turbo
- **12 languages** + auto-detect (Spanish default)
- **Real-time transcription** from microphone via WebSocket
- **Download as** JSON, TXT, or SRT (subtitles)
- **Cancel** running transcriptions at any time

### AI Summarization
- **4 summary types**: General summary, class notes, study guide, or combined
- **3 length options**: Short, medium, or detailed
- **2 AI providers**: Ollama (local) or Gemini (cloud)
- **Multi-transcription**: Combine up to 5 transcriptions into one summary
- **File attachments**: Add PDF, PPTX, or images as extra context
- **Markdown output** with structured headings

### UI
- Dark/light theme toggle
- Responsive sidebar navigation
- Drag-and-drop file upload
- Real-time progress indicators
- Active jobs tracking

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python, Flask, Flask-SocketIO |
| Transcription | faster-whisper, OpenAI Whisper API |
| Summarization | Ollama (local), Gemini API |
| Frontend | Jinja2, vanilla CSS/JS, Inter font |
| Storage | JSON files (no database) |

## Quick Start

```bash
# Clone the repo
git clone https://github.com/brayan083/whisper-bray.git
cd whisper-bray

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys (optional — local mode works without them)

# Run
cd app
python app.py
```

The app runs on **http://localhost:5001** by default.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key (for cloud summaries) | YES |
| `OPENAI_API_KEY` | OpenAI API key (for Whisper API mode) | YES |

## Project Structure

```
app/
├── app.py                 # Entry point
├── config.py              # Settings & paths
├── transcriber.py         # Whisper transcription
├── ai_service.py          # Ollama/Gemini summarization
├── file_parser.py         # PDF/PPTX extraction
├── jobs.py                # In-memory job tracking
├── routes/                # Blueprints (general, transcription, summary, realtime)
├── templates/             # Jinja2 HTML pages
├── static/css/            # Design system & page styles
├── static/js/             # Theme toggle & page scripts
└── data/                  # JSON storage (transcriptions, summaries, settings)
```

## How It Works

1. **Upload** an audio/video file (or use the microphone for real-time transcription)
2. A background thread runs Whisper and streams progress to the frontend
3. **View the transcript** with timestamps, download as TXT/SRT/JSON
4. **Generate a summary** by selecting a transcription, summary type, length, and AI provider
5. View the formatted summary or download it

All data is stored as JSON files in `app/data/` — no database setup required.

## License

MIT
