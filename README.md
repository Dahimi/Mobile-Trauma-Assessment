# 📱 Mobile Trauma Assessment Prototype

A mobile-friendly prototype application for trauma assessment of children affected by war and conflict zones. This Gradio-based interface serves as a proof-of-concept for our comprehensive child trauma assessment platform while the native mobile application is under development.

> **⚠️ Note**: Unfortunately, we weren't able to host this Gradio app on Hugging Face Spaces since HF doesn't allow running background processes (which we need for the Ollama server). Therefore, this prototype requires local installation and setup.

## 🎯 Purpose

This prototype demonstrates our AI-powered trauma assessment capabilities designed specifically for:
- **War-affected children** from conflict zones (Gaza, Ukraine, Syria, Sudan)
- **Mental health professionals** and volunteers working in crisis situations
- **Parents and caregivers** seeking initial trauma screening for their children
- **Integration testing** with the Care Bridge web platform for professional handoff

## 🌟 Key Features

### 🤖 **AI-Powered Conversations**
- **Fine-tuned Gemma 3N model** specialized for child trauma assessment
- **Multilingual support**: Arabic (Palestinian/Syrian/Sudanese dialects), Ukrainian, English
- **Culturally sensitive responses** adapted to specific conflict contexts
- **Real-time conversation** with empathetic, professional tone

### 📊 **Comprehensive Assessment**
- **Structured report generation** using AI-powered analysis
- **Severity scoring** (1-10 scale) with risk stratification
- **Behavioral pattern identification** and trauma indicators
- **Cultural context integration** for region-specific trauma expressions

### 🖼️ **Multimodal Analysis**
- **Image analysis**: Upload child photos or drawings for AI visual assessment
- **Text conversations**: Natural language processing for trauma indicators
- **Audio support**: Coming soon (currently disabled in prototype)

### 🌉 **Care Bridge Integration**
- **Seamless report submission** to professional web platform
- **Real-time specialist monitoring** for professional responses
- **Background polling** for automatic updates from mental health professionals
- **Secure data transmission** with HIPAA compliance standards

## 🚀 Installation & Setup

### Prerequisites

1. **Python 3.8+** with pip
2. **Ollama server** for AI model hosting
3. **Internet connection** for Care Bridge platform integration

### Step 1: Install Ollama

Visit the [official Ollama website](https://ollama.ai) for OS-specific installation instructions:
- **macOS**: `brew install ollama`
- **Linux**: Available via package managers
- **Windows**: Download from official site

### Step 2: Install the Trauma Assessment Model

```bash
# Start Ollama server
ollama serve

# Pull the fine-tuned trauma assessment model
ollama pull llm_hub/child_trauma_gemma
```

### Step 3: Install Python Dependencies

```bash
# Install required packages
pip install gradio requests python-dotenv supabase ollama pydantic
```

### Step 4: Configure Environment

I pushed a `.env` file with the project Supabase credentials (for Care Bridge integration) so that you can test it the complete workflow easily (Don't worry, it's a just dummy project that I created on Supabase):

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

### Step 5: Launch the Application

```bash
# Run the Gradio app
python app.py
```

The application will open in your browser at `http://localhost:7860`

## 🎮 Usage Guide

### 1. **Complete Onboarding**
- Enter child's basic information (name, age, gender, location)
- System automatically adapts cultural context based on location

### 2. **Conduct Assessment**
- Start conversations in any supported language
- Upload relevant images (photos, drawings) for visual analysis
- AI responds with culturally appropriate, empathetic guidance

### 3. **Generate Report**
- Click "Generate Comprehensive Assessment" 
- AI analyzes conversation using structured output
- Comprehensive report generated with severity scoring and recommendations

### 4. **Professional Handoff**
- Push report to Care Bridge platform for specialist review
- Background monitoring for specialist responses
- Manual refresh available for real-time updates

## 🔧 Technical Architecture

- **Frontend**: Gradio web interface optimized for mobile use
- **AI Backend**: Ollama server hosting fine-tuned Gemma 3N model
- **Database**: Supabase for report storage and specialist communication
- **Platform Integration**: RESTful API connection to Care Bridge web platform

## 🌍 Supported Languages & Regions

- **Arabic**: Palestinian/Levantine, Syrian, Sudanese dialects
- **Ukrainian**: Standard Ukrainian with conflict-specific terminology
- **English**: Professional mental health vocabulary
- **Cultural Contexts**: Gaza, West Bank, Ukraine, Syria, Sudan, and others


## 🚧 Development Status

This is a **prototype application** serving as:
- **Proof of concept** for AI trauma assessment capabilities
- **Integration testing** platform for Care Bridge connectivity
- **User experience validation** for mobile trauma assessment workflows
- **Model performance evaluation** in real-world scenarios

**The production mobile application is currently under development**

## 🤝 Integration with Care Bridge Platform

This mobile prototype seamlessly integrates with our Care Bridge web platform, enabling:
- **Professional review** of AI-generated assessments
- **Specialist feedback** and recommendations
- **Care coordination** between multiple providers
- **Longitudinal tracking** of child progress
- **Crisis intervention** alerts when needed

## ⚖️ Disclaimer

This prototype is designed for **screening and initial assessment purposes only**. It does not replace professional mental health evaluation or emergency intervention services. In case of immediate safety concerns, contact local emergency services immediately.

---

*Part of the Child Trauma Assessment AI project - Building technology to support children affected by war and conflict.* 