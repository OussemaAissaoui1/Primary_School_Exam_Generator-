# Primary School Exam Generator 🎓

A Tunisian 6th-grade mathematics exam generator using LangGraph and LLMs. Generates authentic, curriculum-aligned exams in Arabic with automatic grading schemas and correction sheets.

## Features

- ✅ **Real Data Integration**: Uses actual extracted exam data from 29+ Tunisian exam PDFs
- 🤖 **LLM-Powered Generation**: Leverages Groq's LLama 3.3 70B for high-quality exam creation
- 📊 **Multi-Step Workflow**: Analyzer → Curriculum → Generator → Validator → Grading → Correction → PDF Export
- 🌐 **Streamlit Web UI**: User-friendly RTL Arabic interface
- 📄 **PDF Export**: Professional PDF output matching official Tunisian exam format
- 🎯 **Curriculum-Aligned**: Generates exams based on specific trimester requirements

## Technology Stack

- **LangGraph**: Orchestrates the multi-agent workflow
- **LangChain**: LLM integration and prompt management
- **Groq**: Fast LLM inference with LLama 3.3 70B
- **Streamlit**: Web interface
- **ReportLab**: PDF generation with Arabic support
- **Python 3.13+**: Core language

## Project Structure

```
exam_generator/
├── app.py                      # Streamlit web application
├── data/                       # Extracted exam data
│   └── extracted/
│       ├── t1/                # Trimester 1 exams (10 files)
│       ├── t2/                # Trimester 2 exams (9 files)
│       └── t3/                # Trimester 3 exams (10 files)
├── graph/                     # LangGraph workflow
│   ├── graph.py              # Main graph builder
│   ├── state.py              # State definitions
│   └── nodes/
│       ├── analyzer.py        # Loads real exam references
│       ├── curriculum.py      # Trimester curriculum
│       ├── generator.py       # LLM exam generation
│       ├── validator.py       # Validates structure
│       ├── grading_schema.py  # Creates grading criteria
│       ├── correction.py      # Generates solutions
│       ├── exporter.py        # PDF export
│       └── llm_utils.py       # LLM helpers
├── fonts/                     # Arabic fonts (Amiri)
└── output/                    # Generated PDFs

```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/OussemaAissaoui1/Primary_School_Exam_Generator.git
cd Primary_School_Exam_Generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Groq API key:
```bash
GROQ_API_KEY=your_api_key_here
```

4. Run the Streamlit app:
```bash
streamlit run app.py
```

## Usage

1. Open the Streamlit app in your browser
2. Select a trimester (1, 2, or 3)
3. Click "Generate Exam"
4. Wait for the multi-step generation process (analyzer → curriculum → generation → validation → grading → correction → export)
5. Download the generated exam PDF and correction PDF

## Workflow Pipeline

The exam generation follows a 7-node LangGraph pipeline:

1. **Analyzer**: Loads 4 real reference exams from extracted data
2. **Curriculum**: Retrieves trimester-specific learning objectives
3. **Generator**: LLM creates unique multi-step exam (7-10 questions, 20 points)
4. **Validator**: Ensures structure and point distribution are correct
5. **Grading Schema**: Maps questions to evaluation criteria
6. **Correction**: Generates detailed solutions
7. **Exporter**: Produces professional PDFs with Arabic RTL support

## Data Source

The generator uses **real extracted exam data** from 29 authentic Tunisian 6th-grade mathematics exams:
- Trimester 1: 9 exams
- Trimester 2: 9 exams
- Trimester 3: 8 exams

This ensures generated exams match the authentic style, difficulty, and format of official Tunisian exams.

## Key Features

### Exam Quality
- Multi-step questions requiring 2+ calculation steps
- "أثبت أن" (prove that) proof-based questions
- Geometry construction exercises
- Time duration calculations
- Unit conversions
- Percentage problems
- Realistic Tunisian scenarios (agriculture, construction, school trips, etc.)

### Formatting
- Proper Arabic RTL layout
- Official Tunisian exam header format
- Grading criteria table
- Answer spaces with dotted lines
- Professional typography with Amiri font

## Configuration

### LLM Settings
- Model: `llama-3.3-70b-versatile`
- Temperature: 0.8 (for variety)
- Max Tokens: 4096
- Automatic retry on rate limits (20s, 40s, 60s backoff)

### Exam Structure
- 3 exercises per exam
- 7-10 total instructions (questions)
- Total: 20 points
- Each instruction: 1.5-5 points
- Varied question counts per exercise (e.g., 3, 2, 4)

## Development

### Recent Updates
- ✅ Integrated real extracted exam data (replaced synthetic data)
- ✅ Fixed PDF export HTML parsing errors
- ✅ Switched to Groq LLama 3.3 70B for better quality
- ✅ Added variation in question counts per exercise
- ✅ Improved text formatting and ordering
- ✅ Enhanced Arabic place names (no English placeholders)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Author

Oussema Aissaoui

## Acknowledgments

- Tunisian Ministry of Education for exam format standards
- Groq for fast LLM inference
- LangChain & LangGraph teams
