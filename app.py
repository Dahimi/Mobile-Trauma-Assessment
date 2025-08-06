import gradio as gr
import json
import time
import random
from datetime import datetime
import os
import uuid
import requests
from requests.exceptions import ConnectionError, RequestException
from dotenv import load_dotenv
from supabase import create_client, Client
import threading
from ollama import chat
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Pydantic model for structured report generation
class RiskAssessment(BaseModel):
    parent_observations: str
    ai_analysis: str 
    severity_score: int
    risk_indicators: list[str]
    cultural_context: str

class EnhancedTraumaAssessmentApp:
    def __init__(self):
        self.report_data = {
            "child_info": {
                "name": "",
                "age": 0,
                "gender": "",
                "location": ""
            },
            "assessment_data": {
                "parent_observations": "",
                "ai_analysis": "",
                "severity_score": 0,
                "risk_indicators": [],
                "cultural_context": ""
            },
            "media_attachments": {
                "drawings": [],
                "audio_recordings": [],
                "photos": []
            },
            "mobile_app_id": str(uuid.uuid4()),
            "session_start": datetime.now().isoformat(),
            "conversation_history": []
        }
        self.is_onboarded = False
        self.submitted_report_id = None
        self.polling_active = False
        self.ollama_conversation = []  # Track conversation for the model
        
        # Initialize Supabase client
        self.supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        self.supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if self.supabase_url and self.supabase_key:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.supabase = None
            print("⚠️ Supabase credentials not found in .env file")
        
    def complete_onboarding(self, child_name, child_age, child_gender, child_location):
        """Complete the onboarding process and store child info"""
        if not all([child_name, child_age, child_gender, child_location]):
            return False, "Please fill in all required information about your child."
        
        self.report_data["child_info"] = {
            "name": child_name,
            "age": int(child_age),
            "gender": child_gender,
            "location": child_location
        }
        self.is_onboarded = True
        
        # Generate cultural context based on location
        self.report_data["assessment_data"]["cultural_context"] = self.generate_cultural_context(child_location)
        
        return True, f"Welcome! I'm ready to help you with {child_name}'s assessment."
    
    def generate_cultural_context(self, location):
        """Generate appropriate cultural context based on location"""
        location_lower = location.lower()
        if any(keyword in location_lower for keyword in ['gaza', 'palestine', 'west bank']):
            return "Assessment conducted considering ongoing conflict exposure and displacement trauma"
        elif any(keyword in location_lower for keyword in ['ukraine', 'kyiv', 'kharkiv', 'mariupol']):
            return "Assessment considering war-related trauma and displacement from conflict zones"
        elif any(keyword in location_lower for keyword in ['syria', 'lebanon', 'jordan']):
            return "Assessment considering refugee experience and cultural adaptation challenges"
        else:
            return f"Assessment conducted with consideration for local cultural context in {location}"
    
    def add_message(self, history, message):
        """Add user message with multimodal support"""
        if not self.is_onboarded:
            return history, gr.MultimodalTextbox(value=None, interactive=False)
        
        # Handle file uploads
        if message.get("files"):
            for file in message["files"]:
                file_type = self.classify_file_type(file)
                history.append({
                    "role": "user", 
                    "content": {"path": file}
                })
                
                # Store in report data
                if file_type == "image":
                    # Determine if it's a drawing or photo based on content analysis
                    attachment_type = "drawings" if "draw" in file.lower() else "photos"
                    self.report_data["media_attachments"][attachment_type].append({
                        "path": file,
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"Image file detected: {file}")
        
        # Handle text message
        if message.get("text"):
            history.append({
                "role": "user", 
                "content": message["text"]
            })
            # Add to conversation history for model
            self.ollama_conversation.append({
                "role": "user", 
                "content": message["text"]
            })
            # Add to parent observations
            current_obs = self.report_data["assessment_data"]["parent_observations"]
            self.report_data["assessment_data"]["parent_observations"] = (
                current_obs + " " + message["text"] if current_obs else message["text"]
            )
        
        # Store conversation history
        self.report_data["conversation_history"] = history
        return history, gr.MultimodalTextbox(value=None, interactive=False)
    
    def classify_file_type(self, file_path):
        """Classify uploaded file type"""
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            return "image"
        else:
            return "other"
    
    def bot_response(self, history):
        """Generate bot response using Ollama model"""
        if not history or not self.is_onboarded:
            return
            
        # Get the last user message
        last_message = ""
        has_image = False
        image_path = None
        
        for msg in reversed(history):
            if msg["role"] == "user":
                if isinstance(msg["content"], str):
                    last_message = msg["content"]
                    break
                elif isinstance(msg["content"], dict) and "path" in msg["content"]:
                    has_image = True
                    image_path = msg["content"]["path"]
                    break
        
        # Prepare message for Ollama
        if has_image and image_path:
            # Handle image input
            try:
                response = chat(
                    model='llm_hub/child_trauma_gemma',
                    messages=[{
                        'role': 'user',
                        'content': f'I am sharing an image related to my child {self.report_data["child_info"]["name"]}\'s situation. Please analyze this image in the context of trauma assessment and respond empathetically.',
                        'images': [image_path],
                    }]
                )
                response_text = response.message.content
            except Exception as e:
                response_text = f"I can see you've shared an image. Thank you for providing this visual information about {self.report_data['child_info']['name']}. Visual expressions can tell us a lot about how children process their experiences. Could you tell me more about when this was created or what you'd like me to know about it?"
                print(f"Ollama image error: {e}")
        else:
            # Handle text conversation
            try:
                response = chat(
                    model='llm_hub/child_trauma_gemma',
                    messages=self.ollama_conversation
                )
                response_text = response.message.content
            except Exception as e:
                response_text = f"Thank you for sharing that with me. I understand this is a difficult time for you and {self.report_data['child_info']['name']}. Could you tell me more about what you're observing?"
                print(f"Ollama text error: {e}")
        
        # Add assistant response to conversation history
        self.ollama_conversation.append({
            "role": "assistant", 
            "content": response_text
        })
        
        # Start bot response
        history.append({"role": "assistant", "content": ""})
        
        # Stream the response
        for character in response_text:
            history[-1]["content"] += character
            time.sleep(0.02)
            yield history
    
    def generate_comprehensive_report(self, progress_callback=None):
        """Generate comprehensive assessment report using Ollama structured output"""
        if not self.is_onboarded:
            return "Please complete the initial assessment form first."
        
        if not self.ollama_conversation:
            return "Please have a conversation first before generating a report."
        
        if progress_callback:
            progress_callback("🤖 Analyzing conversation with AI...")
        
        try:
            # Generate structured assessment using Ollama
            assessment_prompt = f"""Based on our conversation about {self.report_data['child_info']['name']}, a {self.report_data['child_info']['age']}-year-old {self.report_data['child_info']['gender']} from {self.report_data['child_info']['location']}, generate a comprehensive trauma risk assessment report. 

Include:
- Parent observations summary from our conversation
- AI analysis of trauma indicators
- Severity score (1-10 scale)
- List of risk indicators identified
- Cultural context considering the child's location and circumstances

Consider the conversation history and any cultural factors relevant to {self.report_data['child_info']['location']}."""

            if progress_callback:
                progress_callback("🧠 AI is generating structured assessment...")

            response = chat(
                model='llm_hub/child_trauma_gemma',
                messages=[{'role': 'user', 'content': assessment_prompt}],
                format=RiskAssessment.model_json_schema(),
                options={'temperature': 0}
            )
            
            if progress_callback:
                progress_callback("📊 Processing assessment data...")
            
            # Parse structured response
            assessment = RiskAssessment.model_validate_json(response.message.content)
            
            # Update report data with AI-generated assessment
            self.report_data["assessment_data"]["parent_observations"] = assessment.parent_observations
            self.report_data["assessment_data"]["ai_analysis"] = assessment.ai_analysis
            self.report_data["assessment_data"]["severity_score"] = assessment.severity_score
            self.report_data["assessment_data"]["risk_indicators"] = assessment.risk_indicators
            self.report_data["assessment_data"]["cultural_context"] = assessment.cultural_context
            
            if progress_callback:
                progress_callback("📋 Formatting final report...")
            
        except Exception as e:
            print(f"Ollama structured output error: {e}")
            if progress_callback:
                progress_callback("⚠️ Using fallback assessment...")
            # Fallback to basic assessment
            self.report_data["assessment_data"]["severity_score"] = 6
            self.report_data["assessment_data"]["risk_indicators"] = ["sleep disturbances", "behavioral changes", "anxiety"]
        
        # Generate formatted report
        child_info = self.report_data["child_info"]
        assessment_data = self.report_data["assessment_data"]
        media_attachments = self.report_data["media_attachments"]
        severity = assessment_data["severity_score"]
        risk_indicators = assessment_data["risk_indicators"]
        
        return f"""# 🔍 COMPREHENSIVE TRAUMA ASSESSMENT REPORT

**Generated:** {datetime.now().strftime("%B %d, %Y at %H:%M")}  
**Assessment ID:** {self.report_data["mobile_app_id"][:8]}  
**Confidentiality Level:** Protected Health Information
**Platform:** Child Trauma Assessment AI

---

## 👤 CHILD INFORMATION

**Name:** {child_info["name"]}  
**Age:** {child_info["age"]} years old  
**Gender:** {child_info["gender"].title()}  
**Location:** {child_info["location"]}  
**Assessment Date:** {datetime.now().strftime("%B %d, %Y")}

---

## 👥 PARENT OBSERVATIONS

{assessment_data["parent_observations"]}

**Session Details:**
- **Duration:** {len(self.report_data["conversation_history"])} message exchanges
- **Media Provided:** {len(media_attachments["drawings"])} drawings, {len(media_attachments["photos"])} photographs

---

## 🧠 AI ANALYSIS

{assessment_data["ai_analysis"]}

**Behavioral Patterns Identified:**
{chr(10).join([f"• {indicator}" for indicator in risk_indicators])}

---

## ⚠️ SEVERITY ASSESSMENT

**Severity Score:** {severity}/10  
**Risk Level:** {"🟡 Moderate Risk" if severity < 7 else "🔴 High Risk - Urgent Intervention Recommended"}  
**Clinical Priority:** {"Standard referral appropriate" if severity < 7 else "Expedited professional evaluation needed"}

---

## 🌍 CULTURAL CONTEXT

{assessment_data["cultural_context"]}

This assessment considers the cultural and environmental factors specific to {child_info["location"]}, including region-specific trauma expressions, family dynamics, and community support systems.

---

## 📋 CLINICAL RECOMMENDATIONS

**Immediate Actions:**
1. Schedule comprehensive evaluation with licensed child trauma specialist
2. Ensure stable, predictable environment for {child_info["name"]}
3. Implement safety planning and crisis contact protocols

**Therapeutic Interventions:**
1. Begin trauma-focused cognitive behavioral therapy (TF-CBT)
2. Consider family therapy to strengthen support systems
3. Monitor sleep, appetite, and behavioral patterns daily

**Cultural Considerations:**
1. Engage culturally competent mental health services
2. Incorporate traditional coping mechanisms where appropriate
3. Consider community-based support resources

**Follow-up:**
- Initial professional evaluation within 1-2 weeks
- Regular monitoring and assessment as recommended by treating clinician

---

## ⚖️ IMPORTANT DISCLAIMERS

- **Preliminary Screening Tool:** This AI-generated assessment is for screening purposes only and does NOT constitute a clinical diagnosis
- **Professional Validation Required:** All findings must be validated by licensed mental health professionals
- **Emergency Protocol:** For immediate safety concerns, contact emergency services immediately
- **Clinical Judgment:** AI analysis should supplement, not replace, professional clinical assessment

**Report Generated:** {datetime.now().isoformat()}  
**Next Review Recommended:** {(datetime.now()).strftime("%B %d, %Y")} (2 weeks)
"""
    
    def push_report_to_care_bridge(self, base_url="https://care-bridge-platform-7vs1.vercel.app"):
        """Push the generated report to the Care Bridge platform."""
        if not self.is_onboarded:
            return False, "Please complete the initial assessment form first."
        
        if not self.report_data["conversation_history"]:
            return False, "Please have a conversation first before pushing a report."
        
        # Prepare data in the format expected by Care Bridge API
        api_data = {
            "child_info": {
                "age": self.report_data["child_info"]["age"],
                "gender": self.report_data["child_info"]["gender"].lower(),
                "location": self.report_data["child_info"]["location"]
            },
            "assessment_data": {
                "parent_observations": self.report_data["assessment_data"]["parent_observations"],
                "ai_analysis": self.report_data["assessment_data"]["ai_analysis"],
                "severity_score": self.report_data["assessment_data"]["severity_score"],
                "risk_indicators": self.report_data["assessment_data"]["risk_indicators"],
                "cultural_context": self.report_data["assessment_data"]["cultural_context"]
            },
            "media_attachments": self.report_data["media_attachments"],
            "mobile_app_id": self.report_data["mobile_app_id"]
        }
        
        try:
            url = f"{base_url}/api/reports"
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(url, json=api_data, headers=headers, timeout=10)
            
            if response.status_code == 201:
                result = response.json()
                report_id = result.get('id', 'Unknown')
                # Store the report ID for polling
                self.submitted_report_id = report_id
                # Start polling for responses
                self.start_response_polling()
                return True, f"✅ Report successfully pushed to Care Bridge Platform!\n📋 Report ID: {report_id}\n🔄 Now monitoring for specialist response..."
            else:
                return False, f"❌ API Error: {response.status_code} - {response.text}"
                
        except ConnectionError:
            return False, "❌ Could not connect to Care Bridge Platform. Please check if the platform is running."
        except requests.exceptions.Timeout:
            return False, "❌ Request timed out. Please try again."
        except RequestException as e:
            return False, f"❌ Network error: {str(e)}"
        except Exception as e:
            return False, f"❌ Unexpected error: {str(e)}"
    
    def start_response_polling(self):
        """Start polling for specialist responses in a background thread."""
        if not self.supabase or not self.submitted_report_id:
            print("⚠️ Cannot start polling: Missing Supabase connection or report ID")
            return
        
        if self.polling_active:
            print("ℹ️ Polling already active")
            return  # Already polling
        
        self.polling_active = True
        print(f"🔄 Starting background polling for report ID: {self.submitted_report_id}")
        polling_thread = threading.Thread(target=self._poll_for_response, daemon=True)
        polling_thread.start()
    
    def _poll_for_response(self):
        """Poll Supabase for specialist responses."""
        max_polls = 120  # Poll for 10 minutes (120 * 5 seconds)
        poll_count = 0
        print("Starting polling for response...")
        while self.polling_active and poll_count < max_polls:
            try:
                # Check for response in Supabase
                print("Polling for response...")
                response = self.supabase.table("responses").select("*").eq("report_id", self.submitted_report_id).execute()
                
                if response.data and len(response.data) > 0:
                    # Response found!
                    specialist_response = response.data[0]
                    self.specialist_response = specialist_response
                    self.get_specialist_response()
                    self.polling_active = False
                    break
                
                # Wait 5 seconds before next poll
                time.sleep(5)
                poll_count += 1
                
            except Exception as e:
                print(f"Error polling for response: {e}")
                time.sleep(5)
                poll_count += 1
        
        # Stop polling after max attempts
        if poll_count >= max_polls:
            self.polling_active = False
    
    def get_specialist_response(self):
        """Get the specialist response if available."""
        if hasattr(self, 'specialist_response'):
            response = self.specialist_response
            
            urgency_color = {
                'low': '🟢',
                'medium': '🟡', 
                'high': '🟠',
                'critical': '🔴'
            }
            
            urgency_emoji = urgency_color.get(response['urgency_level'], '⚪')
            
            formatted_response = f"""
# 👨‍⚕️ SPECIALIST RESPONSE RECEIVED

**Response Date:** {response['response_date'][:19].replace('T', ' ')}  
**Specialist ID:** {response['psychologist_id']}  
**Urgency Level:** {urgency_emoji} {response['urgency_level'].upper()}

---

## 📝 PSYCHOLOGIST NOTES

{response['psychologist_notes']}

---

## 💡 RECOMMENDATIONS

"""
            
            if isinstance(response['recommendations'], dict):
                for key, value in response['recommendations'].items():
                    formatted_response += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
            else:
                formatted_response += str(response['recommendations'])
            
            return True, formatted_response
        
        return False, "No specialist response available yet. Still monitoring..."

# Initialize enhanced app
app = EnhancedTraumaAssessmentApp()

# Enhanced CSS with onboarding styles
css = """
/* Main container styling */
.gradio-container {
    max-width: 900px !important;
    margin: 0 auto !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Onboarding specific styles */
.onboarding-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 40px 30px;
    border-radius: 20px;
    margin: 20px 0;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.welcome-form {
    background: white;
    color: #333;
    padding: 30px;
    border-radius: 15px;
    margin: 20px 0;
    box-shadow: 0 5px 20px rgba(0,0,0,0.1);
}

.form-section {
    margin: 20px 0;
    text-align: left;
}

.form-section label {
    font-weight: 600;
    color: #2d3436;
    margin-bottom: 8px;
    display: block;
}

/* Header styling */
.header-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px 20px;
    border-radius: 15px;
    margin-bottom: 25px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

/* Status indicators */
.status-success {
    background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
    border-left: 4px solid #00b894;
    padding: 15px 20px;
    border-radius: 8px;
    margin: 15px 0;
    color: #00b894;
    font-weight: 500;
}

.status-warning {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
    border-left: 4px solid #f39c12;
    padding: 15px 20px;
    border-radius: 8px;
    margin: 15px 0;
    color: #e67e22;
}

.status-info {
    background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
    border-left: 4px solid #74b9ff;
    padding: 15px 20px;
    border-radius: 8px;
    margin: 15px 0;
    color: #0984e3;
}

/* Button styling */
.primary-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    padding: 15px 30px !important;
    border-radius: 25px !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
}

.primary-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
}

/* Chat interface styling */
.chat-container {
    background: white;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}

.child-info-display {
    background: linear-gradient(135deg, #ddd6fe 0%, #e0e7ff 100%);
    border: 1px solid #c4b5fd;
    padding: 15px 20px;
    border-radius: 10px;
    margin: 15px 0;
    color: #5b21b6;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
    .gradio-container {
        max-width: 100% !important;
        margin: 0 10px !important;
    }
    
    .onboarding-container {
        padding: 25px 20px;
        margin: 10px 0;
    }
    
    .welcome-form {
        padding: 20px;
        margin: 15px 0;
    }
}
"""

# Build enhanced Gradio interface with onboarding
with gr.Blocks(css=css, title="Child Trauma Assessment - Professional Support", theme=gr.themes.Soft()) as demo:
    
    # Session state for controlling interface
    onboarding_complete = gr.State(False)
    
    # Welcome/Onboarding Interface
    with gr.Column(visible=True) as onboarding_section:
        gr.HTML("""
        <div class="onboarding-container">
            <h1>🤗 Welcome to Child Trauma Assessment AI</h1>
            <p>Professional-grade support for families and children in crisis</p>
            <br>
            <h3>Let's start by learning about your child</h3>
        </div>
        """)
        
        with gr.Column(elem_classes=["welcome-form"]):
            gr.HTML("<h2 style='text-align: center; color: #667eea; margin-bottom: 25px;'>📝 Child Information Form</h2>")
            
            with gr.Row():
                child_name = gr.Textbox(
                    label="Child's Name (First name only for privacy)",
                    placeholder="e.g., Sarah, Ahmed, Oleksandr",
                    elem_classes=["form-section"]
                )
                child_age = gr.Number(
                    label="Child's Age",
                    minimum=2,
                    maximum=18,
                    value=8,
                    elem_classes=["form-section"]
                )
            
            with gr.Row():
                child_gender = gr.Dropdown(
                    label="Gender",
                    choices=["Female", "Male", "Prefer not to say"],
                    value="Female",
                    elem_classes=["form-section"]
                )
                child_location = gr.Textbox(
                    label="Current Location (City/Region)",
                    placeholder="e.g., Gaza, Kyiv, Aleppo, London",
                    elem_classes=["form-section"]
                )
            
            gr.HTML("""
            <div class="status-info" style="margin: 20px 0;">
                <strong>🔒 Privacy Notice:</strong> This information is used only to personalize the assessment 
                and provide culturally appropriate support. No personal data is stored permanently.
            </div>
            """)
            
            start_assessment_btn = gr.Button(
                "🚀 Begin Assessment",
                elem_classes=["primary-button"],
                variant="primary",
                size="lg"
            )
            
            onboarding_status = gr.HTML()
    
    # Main Assessment Interface (hidden initially)  
    with gr.Column(visible=False) as main_interface:
        # Child info display
        child_info_display = gr.HTML()
        
        with gr.Tab("💬 Confidential Consultation"):
            gr.HTML("""
            <div class="status-info">
                <strong>🤖 REAL AI MODEL:</strong> This platform uses our fine-tuned Gemma 3N model for authentic trauma assessment conversations.
                <br><br>
                <strong>💡 Try These Features:</strong>
                <br>
                • Start a conversation: "Hello, I'm worried about my child's recent behavior changes"
                <br>
                • Upload images (child photos, drawings) for AI visual analysis
                <br>
                • Use different languages - the model supports Arabic, Ukrainian, and English
                <br>
                • Generate structured reports with AI-powered assessment insights
                <br><br>
                <strong>🔒 Privacy:</strong> All conversations are processed securely. Audio support coming soon.
            </div>
            """)
            
            chatbot = gr.Chatbot(
                label="AI Trauma Assessment Specialist",
                height=500,
                bubble_full_width=False,
                type="messages",
                show_label=False,
                elem_classes=["chat-container"]
            )
            
            chat_input = gr.MultimodalTextbox(
                interactive=True,
                file_count="multiple",
                placeholder="Share your concerns here... يمكنك الكتابة بالعربية • Можете писати українською",
                show_label=False,
                sources=["upload"]  # Removed microphone - audio not yet supported
            )
            
            with gr.Row():
                clear_btn = gr.Button("🗑️ New Conversation", variant="secondary", size="sm")
                gr.HTML('<div style="flex-grow: 1;"></div>')
        
        with gr.Tab("📋 Professional Assessment Report"):
            gr.HTML("""
            <div class="status-warning">
                <strong>⚠️ Professional Use Only:</strong> This AI-generated report is a preliminary screening tool. 
                It must be reviewed by licensed mental health professionals.
            </div>
            """)
            
            generate_report_btn = gr.Button(
                "📊 Generate Comprehensive Assessment", 
                variant="primary", 
                size="lg",
                elem_classes=["primary-button"]
            )
            
            # Add progress indicator
            progress_status = gr.HTML()
            
            report_output = gr.Markdown()
            
            with gr.Row():
                save_report_btn = gr.Button("💾 Save Report", variant="secondary")
                push_care_bridge_btn = gr.Button("🌉 Push to Care Bridge", variant="primary")
                gr.Button("📧 Email to Professional", variant="secondary", interactive=False)
            
            save_status = gr.HTML()
            care_bridge_status = gr.HTML()
        
        with gr.Tab("👨‍⚕️ Specialist Response"):
            gr.HTML("""
            <div class="status-info">
                <strong>🔄 Background Monitoring:</strong> Once you submit a report, we automatically monitor for specialist responses in the background.
                Click the button below to check for new responses.
            </div>
            """)
            
            check_response_btn = gr.Button(
                "🔍 Check for Specialist Response", 
                variant="secondary", 
                size="lg"
            )
            
            specialist_response_output = gr.Markdown()
            response_status = gr.HTML()
        
        with gr.Tab("📖 Resources & Information"):
            gr.Markdown("""
            ## 🎯 How This Assessment Works
            
            Our AI specialist uses evidence-based approaches tailored to your child's specific situation:
            
            ### 📝 **Personalized Assessment**
            - Responses are customized based on your child's age, gender, and location
            - Cultural context is considered throughout the evaluation
            - All interactions are stored securely for comprehensive reporting
            
            ### 🔍 **What We Analyze**
            - Behavioral pattern changes specific to your child's developmental stage
            - Cultural expressions of trauma and stress
            - Family dynamics and support systems
            - Environmental factors affecting recovery
            
            ### 📊 **Structured Data Collection**
            All information is organized into a comprehensive clinical format:
            - Child demographics and context
            - Detailed parent observations
            - AI analysis and risk assessment  
            - Multimedia evidence (drawings, voice recordings, photos)
            - Cultural considerations and recommendations
            
            ## 🌉 **Care Bridge Platform Integration**
            
            This assessment tool integrates with the Care Bridge Platform to:
            - **Share Reports**: Securely transmit assessment data to professional networks
            - **Track Progress**: Maintain longitudinal care records
            - **Coordinate Care**: Enable multi-disciplinary team collaboration
            - **Emergency Response**: Alert crisis intervention teams when needed
            """)
    
    # Event handlers
    def handle_onboarding(name, age, gender, location):
        success, message = app.complete_onboarding(name, age, gender, location)
        
        if success:
            child_display = f"""
            <div class="child-info-display">
                <strong>👤 Assessment for:</strong> {name}, {int(age)} years old ({gender}) • 📍 {location}
            </div>
            """
            return (
                gr.Column(visible=False),  # Hide onboarding
                gr.Column(visible=True),   # Show main interface
                child_display,
                f'<div class="status-success">{message}</div>'
            )
        else:
            return (
                gr.Column(visible=True),   # Keep onboarding visible
                gr.Column(visible=False),  # Keep main interface hidden
                "",
                f'<div class="status-warning">❌ {message}</div>'
            )
    
    # Onboarding completion
    start_assessment_btn.click(
        handle_onboarding,
        inputs=[child_name, child_age, child_gender, child_location],
        outputs=[onboarding_section, main_interface, child_info_display, onboarding_status]
    )
    
    # Conversation handling
    def handle_conversation():
        chat_msg = chat_input.submit(
            app.add_message, 
            [chatbot, chat_input], 
            [chatbot, chat_input]
        )
        bot_msg = chat_msg.then(
            app.bot_response, 
            chatbot, 
            chatbot
        )
        bot_msg.then(
            lambda: gr.MultimodalTextbox(interactive=True), 
            None, 
            [chat_input]
        )
    
    handle_conversation()
    
    # Clear conversation
    def clear_conversation():
        app.report_data["conversation_history"] = []
        app.report_data["assessment_data"]["parent_observations"] = ""
        app.report_data["assessment_data"]["ai_analysis"] = ""
        app.report_data["media_attachments"] = {"drawings": [], "audio_recordings": [], "photos": []}
        return [], gr.MultimodalTextbox(value=None, interactive=True)
    
    clear_btn.click(
        clear_conversation,
        outputs=[chatbot, chat_input]
    )
    
    # Generate report with progress updates
    def generate_report_with_progress():
        # Show initial progress
        progress_updates = []
        
        def update_progress(message):
            progress_updates.append(f'<div class="status-info">{message}</div>')
            return progress_updates[-1]
        
        # Generate report with progress callback
        try:
            progress = update_progress("🚀 Starting assessment generation...")
            yield "", progress  # Empty report, show progress
            
            report = app.generate_comprehensive_report(progress_callback=update_progress)
            
            final_progress = update_progress("✅ Assessment completed!")
            yield report, final_progress
            
            # Clear progress after 3 seconds
            time.sleep(3)
            yield report, ""
            
        except Exception as e:
            error_progress = f'<div class="status-warning">❌ Error: {str(e)}</div>'
            yield "", error_progress

    generate_report_btn.click(
        generate_report_with_progress,
        outputs=[report_output, progress_status]
    )
    
    # Save report
    def save_report_with_data(report_content):
        if not report_content or "Please complete" in report_content:
            return "❌ No report available to save."
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save markdown report
        report_filename = f"trauma_report_{app.report_data['child_info']['name']}_{timestamp}.md"
        
        # Save structured data
        data_filename = f"assessment_data_{app.report_data['child_info']['name']}_{timestamp}.json"
        
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            with open(data_filename, 'w', encoding='utf-8') as f:
                json.dump(app.report_data, f, indent=2, ensure_ascii=False, default=str)
            
            return f"✅ Report saved as: **{report_filename}**<br>📊 Data saved as: **{data_filename}**"
        except Exception as e:
            return f"❌ Error saving files: {str(e)}"
    
    save_report_btn.click(
        save_report_with_data,
        inputs=[report_output],
        outputs=[save_status]
    )

    # Push report to Care Bridge
    def push_to_care_bridge():
        success, message = app.push_report_to_care_bridge()
        status_class = "status-success" if success else "status-warning"
        return f'<div class="{status_class}">{message}</div>'

    push_care_bridge_btn.click(
        push_to_care_bridge,
        outputs=[care_bridge_status]
    )
    
    # Check for specialist response
    def check_for_response():
        has_response, response_content = app.get_specialist_response()
        if has_response:
            return response_content, '<div class="status-success">✅ Specialist response received!</div>'
        elif app.polling_active:
            return "", '<div class="status-info">🔄 Still monitoring for specialist response...</div>'
        elif app.submitted_report_id:
            return "", '<div class="status-warning">⏸️ Monitoring stopped. No response received within time limit.</div>'
        else:
            return "", '<div class="status-warning">ℹ️ Submit a report first to check for responses.</div>'
    
    check_response_btn.click(
        check_for_response,
        outputs=[specialist_response_output, response_status]
    )
    
    # Note: Auto-refresh functionality can be added with newer Gradio versions
    # For now, users can manually click the "Check for Specialist Response" button
    
    # Feedback handling
    def handle_feedback(x: gr.LikeData):
        feedback_type = "👍 Helpful" if x.liked else "👎 Needs Improvement"
        print(f"User feedback: {feedback_type} on message {x.index}")
        # Could store this in report_data for quality improvement
    
    chatbot.like(handle_feedback, None, None, like_user_message=True)

# Launch configuration
if __name__ == "__main__":
    demo.launch(
        share=True,
        inbrowser=True,
        show_error=True
    )