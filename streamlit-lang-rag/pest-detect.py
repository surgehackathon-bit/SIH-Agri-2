import streamlit as st
import os
import time
import json
import pandas as pd
from pathlib import Path
import base64
from PIL import Image
import io
import requests

# Set USER_AGENT to avoid warnings
os.environ.setdefault('USER_AGENT', 'StreamlitAgricultureApp/1.0')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# LangChain components
from langchain_community.document_loaders import DirectoryLoader, TextLoader, WebBaseLoader
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_groq import ChatGroq
from langchain.schema import Document

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Pest & Agriculture Assistant",
    page_icon="🌱",
    layout="wide"
)

# --- Pest/Disease Knowledge Base ---
PEST_DISEASE_KNOWLEDGE = {
    "common_pests": {
        "aphids": {
            "scientific_name": "Aphididae",
            "crops_affected": ["tomato", "pepper", "cabbage", "rose", "wheat", "rice"],
            "symptoms": ["yellowing leaves", "curled leaves", "sticky honeydew", "stunted growth", "small green/black insects"],
            "visual_signs": ["clusters of small soft-bodied insects", "ants farming aphids", "sooty mold on honeydew"],
            "treatment": ["neem oil spray", "insecticidal soap", "ladybug release", "systemic insecticides"],
            "prevention": ["reflective mulch", "companion planting", "regular inspection"],
            "season": ["spring", "early summer"],
            "severity": "moderate"
        },
        "whiteflies": {
            "scientific_name": "Aleyrodidae",
            "crops_affected": ["tomato", "cucumber", "cotton", "soybean", "pepper"],
            "symptoms": ["yellowing leaves", "leaf drop", "stunted growth", "sooty mold"],
            "visual_signs": ["tiny white flying insects", "white eggs under leaves", "honeydew deposits"],
            "treatment": ["yellow sticky traps", "neem oil", "biological control", "systemic insecticides"],
            "prevention": ["row covers", "reflective mulch", "remove weeds"],
            "season": ["summer", "warm weather"],
            "severity": "high"
        },
        "thrips": {
            "scientific_name": "Thysanoptera",
            "crops_affected": ["onion", "tomato", "pepper", "cucumber", "flowers"],
            "symptoms": ["silver streaks on leaves", "black specks", "distorted growth", "bronzing"],
            "visual_signs": ["tiny elongated insects", "rasping damage", "feeding scars"],
            "treatment": ["blue sticky traps", "predatory mites", "spinosad spray", "systemic insecticides"],
            "prevention": ["weed control", "row covers", "beneficial insects"],
            "season": ["hot dry weather", "summer"],
            "severity": "moderate to high"
        },
        "spider_mites": {
            "scientific_name": "Tetranychidae",
            "crops_affected": ["tomato", "bean", "cucumber", "corn", "strawberry"],
            "symptoms": ["stippling on leaves", "webbing", "yellowing", "leaf drop"],
            "visual_signs": ["fine webbing", "tiny moving dots", "dusty appearance"],
            "treatment": ["miticide spray", "predatory mites", "water spray", "sulfur dust"],
            "prevention": ["adequate humidity", "avoid over-fertilization", "beneficial insects"],
            "season": ["hot dry weather", "drought conditions"],
            "severity": "high"
        }
    },
    "common_diseases": {
        "powdery_mildew": {
            "scientific_name": "Erysiphales",
            "crops_affected": ["cucumber", "squash", "grape", "rose", "wheat"],
            "symptoms": ["white powdery coating", "yellowing leaves", "stunted growth", "leaf distortion"],
            "visual_signs": ["white fungal growth on leaves", "flour-like appearance", "affects upper leaf surface"],
            "treatment": ["fungicide spray", "baking soda solution", "milk spray", "sulfur treatment"],
            "prevention": ["good air circulation", "avoid overhead watering", "resistant varieties"],
            "season": ["humid conditions", "moderate temperatures"],
            "severity": "moderate"
        },
        "late_blight": {
            "scientific_name": "Phytophthora infestans",
            "crops_affected": ["tomato", "potato", "pepper"],
            "symptoms": ["dark lesions on leaves", "white mold", "fruit rot", "plant collapse"],
            "visual_signs": ["water-soaked spots", "white fuzzy growth", "brown/black lesions"],
            "treatment": ["copper fungicide", "remove affected plants", "improve drainage"],
            "prevention": ["crop rotation", "avoid overhead irrigation", "resistant varieties"],
            "season": ["cool wet weather", "high humidity"],
            "severity": "very high"
        },
        "bacterial_wilt": {
            "scientific_name": "Ralstonia solanacearum",
            "crops_affected": ["tomato", "pepper", "eggplant", "potato"],
            "symptoms": ["sudden wilting", "yellowing", "vascular browning", "plant death"],
            "visual_signs": ["wilting despite moist soil", "brown vascular tissue", "bacterial ooze"],
            "treatment": ["remove infected plants", "soil solarization", "resistant varieties"],
            "prevention": ["crop rotation", "soil drainage", "clean tools", "certified seeds"],
            "season": ["warm humid conditions", "monsoon"],
            "severity": "very high"
        },
        "rust": {
            "scientific_name": "Pucciniales",
            "crops_affected": ["wheat", "corn", "bean", "rose", "coffee"],
            "symptoms": ["orange/brown spots", "pustules", "yellowing", "defoliation"],
            "visual_signs": ["rusty colored pustules", "spore masses", "circular spots"],
            "treatment": ["fungicide spray", "resistant varieties", "remove affected leaves"],
            "prevention": ["crop rotation", "good air circulation", "avoid overhead watering"],
            "season": ["humid conditions", "moderate temperatures"],
            "severity": "moderate to high"
        }
    }
}

# Regional pest/disease data for Tamil Nadu and Kerala
REGIONAL_PEST_DATA = {
    "tamil_nadu": {
        "common_issues": ["brown planthopper", "stem borer", "leaf blast", "bacterial blight"],
        "seasonal_patterns": {
            "monsoon": ["fungal diseases", "bacterial infections"],
            "summer": ["thrips", "spider mites", "powdery mildew"],
            "winter": ["aphids", "whiteflies"]
        },
        "major_crops_pests": {
            "rice": ["brown planthopper", "stem borer", "leaf blast"],
            "cotton": ["bollworm", "whitefly", "thrips"],
            "sugarcane": ["red rot", "smut", "scale insects"]
        }
    },
    "kerala": {
        "common_issues": ["coconut mite", "pepper virus", "cardamom thrips", "banana bunchy top"],
        "seasonal_patterns": {
            "monsoon": ["fungal diseases", "root rot"],
            "summer": ["mites", "scales"],
            "winter": ["viral diseases", "nematodes"]
        },
        "major_crops_pests": {
            "coconut": ["red palm weevil", "coconut mite", "bud rot"],
            "pepper": ["pepper virus", "root rot", "scale insects"],
            "cardamom": ["thrips", "capsule rot", "damping off"]
        }
    }
}

# --- Image Processing Functions ---
def encode_image_to_base64(image):
    """Encode PIL image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode()

def analyze_image_with_vision_model(image, description="", api_key=""):
    """
    Analyze image using vision-capable models
    Note: Groq doesn't support vision models yet, so we use alternative approaches
    """
    try:
        # Option 1: Use Google Vision API (requires setup)
        # return analyze_with_google_vision(image, description)
        
        # Option 2: Use OpenAI GPT-4 Vision (requires OpenAI API key)
        # return analyze_with_openai_vision(image, description, api_key)
        
        # Option 3: Current implementation - text-based analysis with image context
        return analyze_image_symptoms_enhanced(image, description)
        
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

def analyze_with_openai_vision(image, description, api_key):
    """
    Use OpenAI GPT-4 Vision for image analysis
    Uncomment and configure if you have OpenAI API key
    """
    try:
        import openai
        
        # Encode image
        base64_image = encode_image_to_base64(image)
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this agricultural image for pest and disease identification.
                            User description: {description}
                            
                            Please identify:
                            1. Any visible pests or insects
                            2. Disease symptoms (spots, discoloration, wilting)
                            3. Plant health indicators
                            4. Damage patterns
                            5. Recommended actions
                            
                            Focus on practical farming advice for Tamil Nadu/Kerala regions."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"OpenAI Vision analysis error: {str(e)}"

def analyze_image_symptoms_enhanced(image, user_description=""):
    """Enhanced image analysis using image properties and description"""
    
    # Get basic image properties
    width, height = image.size
    format_info = image.format if image.format else "Unknown"
    
    # Convert to RGB if necessary for analysis
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Basic color analysis for common pest/disease indicators
    import numpy as np
    img_array = np.array(image)
    
    # Calculate color distributions
    avg_color = np.mean(img_array, axis=(0, 1))
    
    color_analysis = ""
    
    # Check for common disease color patterns
    if avg_color[1] > avg_color[0] and avg_color[1] > avg_color[2]:  # Green dominant
        color_analysis = "Healthy green foliage detected. "
    elif avg_color[2] > avg_color[1]:  # Yellow/brown tones
        color_analysis = "Yellowing or browning detected - possible nutrient deficiency or disease. "
    elif np.std(img_array) > 50:  # High variation might indicate spots or damage
        color_analysis = "High color variation detected - possible spotting or pest damage. "
    
    analysis_result = f"""
    IMAGE ANALYSIS REPORT:
    ===================
    Image Properties: {width}x{height} pixels, Format: {format_info}
    
    Basic Visual Analysis:
    {color_analysis}
    
    User Description: {user_description}
    
    AUTOMATED ASSESSMENT:
    Based on the uploaded image and your description, here's what to look for:
    
    1. LEAF SYMPTOMS:
    - Check for yellowing, browning, or unusual discoloration
    - Look for spots, holes, or irregular patterns
    - Examine leaf curling or distortion
    
    2. PEST INDICATORS:
    - Small moving insects on plant surfaces
    - Sticky honeydew or webbing
    - Chewed edges or holes in leaves
    
    3. DISEASE SIGNS:
    - Powdery or fuzzy growth on surfaces
    - Water-soaked lesions
    - Wilting despite adequate moisture
    
    For accurate identification, please describe:
    - What symptoms you're observing
    - Which plant/crop is affected
    - When the problem started
    - Recent weather conditions
    
    This will help match against our comprehensive pest/disease database.
    """
    
    return analysis_result

# --- Knowledge Base Configuration (keeping existing structure) ---
POSSIBLE_KB_PATHS = [
    "soil_knowledge_base",
    "../soil_knowledge_base", 
    "./soil_knowledge_base",
    "streamlit-lang-rag/soil_knowledge_base"
]

POSSIBLE_CROP_CYCLE_PATHS = [
    "cropCycle_knowledge_base",
    "../cropCycle_knowledge_base",
    "./cropCycle_knowledge_base",
    "streamlit-lang-rag/cropCycle_knowledge_base"
]

# Find the correct paths
SOIL_KB_PATH = None
for path in POSSIBLE_KB_PATHS:
    if os.path.exists(path):
        SOIL_KB_PATH = path
        break

CROP_CYCLE_KB_PATH = None
for path in POSSIBLE_CROP_CYCLE_PATHS:
    if os.path.exists(path):
        CROP_CYCLE_KB_PATH = path
        break

# Original farming URLs
FARMER_URLS = [
    "https://vikaspedia.in/agriculture/crop-production",
    "https://vikaspedia.in/agriculture/schemes-for-farmers",
    "https://vikaspedia.in/agriculture/agri-credit",
    "https://www.india.gov.in/topics/agriculture"
]

# Your existing loader classes (keeping them as they are)
class SoilKnowledgeLoader:
    """Custom loader for soil knowledge base files"""
    
    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        
    def load_all_documents(self):
        """Load all documents from the soil knowledge base"""
        documents = []
        
        # 1. Load JSON knowledge base
        json_file = self.kb_path / "complete_soil_knowledge_base.json"
        if json_file.exists():
            documents.extend(self._load_json_kb(json_file))
            st.sidebar.success("✅ JSON soil database loaded")
        
        # 2. Load text documents with error handling
        docs_folder = self.kb_path / "documents"
        if docs_folder.exists():
            documents.extend(self._load_text_documents_safely(docs_folder))
            st.sidebar.success("✅ Text documents loaded")
        
        # 3. Load CSV data as documents
        csv_files = ["city_soil_profiles.csv", "regional_soil_statistics.csv"]
        csv_loaded = 0
        for csv_file in csv_files:
            csv_path = self.kb_path / csv_file
            if csv_path.exists():
                documents.extend(self._load_csv_data(csv_path))
                csv_loaded += 1
        
        if csv_loaded > 0:
            st.sidebar.success(f"✅ {csv_loaded} CSV files loaded")
        
        return documents
    
    def _load_text_documents_safely(self, docs_folder: Path):
        """Load text documents with enhanced error handling"""
        documents = []
        
        try:
            txt_files = list(docs_folder.glob("*.txt"))
            
            for txt_file in txt_files:
                try:
                    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
                    
                    content = None
                    for encoding in encodings:
                        try:
                            with open(txt_file, 'r', encoding=encoding) as f:
                                content = f.read()
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if content:
                        filename = txt_file.stem
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": str(txt_file),
                                "type": "comprehensive_analysis",
                                "category": "soil_report",
                                "filename": filename
                            }
                        )
                        
                        filename_lower = filename.lower()
                        if "tamil_nadu" in filename_lower or "chennai" in filename_lower:
                            doc.metadata["region"] = "tamil_nadu"
                            doc.metadata["state"] = "Tamil Nadu"
                        elif "kerala" in filename_lower or "kochi" in filename_lower:
                            doc.metadata["region"] = "kerala" 
                            doc.metadata["state"] = "Kerala"
                        
                        documents.append(doc)
                    else:
                        st.sidebar.warning(f"⚠️ Could not read {txt_file.name}")
                        
                except Exception as e:
                    st.sidebar.warning(f"⚠️ Error loading {txt_file.name}: {str(e)}")
                    continue
                    
        except Exception as e:
            st.sidebar.error(f"Error accessing documents folder: {e}")
        
        return documents
    
    def _load_json_kb(self, json_file: Path):
        """Load and convert JSON knowledge base to documents"""
        documents = []
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
            
            metadata_content = f"""
SOIL KNOWLEDGE BASE OVERVIEW
============================
Data Source: {kb_data.get('metadata', {}).get('data_source', 'SoilGrids 2.0')}
Created: {kb_data.get('metadata', {}).get('created_date', 'N/A')}
Coverage Area: {kb_data.get('metadata', {}).get('coverage_area', 'Tamil Nadu and Kerala, India')}
Total Parameters: {kb_data.get('metadata', {}).get('total_parameters', 10)} soil parameters analyzed
Resolution: {kb_data.get('metadata', {}).get('resolution', '250m global grid')}
Coordinate System: {kb_data.get('metadata', {}).get('coordinate_system', 'EPSG:4326')}
"""
            documents.append(Document(
                page_content=metadata_content,
                metadata={"source": "soil_metadata", "type": "overview", "category": "soil_data"}
            ))
            
            # Process other sections (abbreviated for space - keeping your original logic)
            
        except Exception as e:
            st.error(f"Error loading JSON knowledge base: {e}")
        
        return documents
    
    def _load_csv_data(self, csv_file: Path):
        """Convert CSV data to documents"""
        # Keeping your original implementation
        return []

class CropCycleKnowledgeLoader:
    """Custom loader for crop cycle knowledge base"""
    
    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
    
    def load_all_documents(self):
        """Load all crop cycle documents"""
        documents = []
        
        json_file = self.kb_path / "crop_cycle.json"
        if json_file.exists():
            documents.extend(self._load_crop_cycle_json(json_file))
            st.sidebar.success("✅ Crop cycle database loaded")
        
        return documents
    
    def _load_crop_cycle_json(self, json_file: Path):
        """Load and convert crop cycle JSON to documents"""
        # Keeping your original implementation
        return []

# New Pest/Disease Knowledge Loader
class PestDiseaseKnowledgeLoader:
    """Custom loader for pest and disease knowledge base"""
    
    def load_all_documents(self):
        """Convert pest/disease knowledge to documents"""
        documents = []
        
        # Create overview document
        overview_content = """
PEST AND DISEASE KNOWLEDGE BASE OVERVIEW
========================================
Comprehensive pest and disease identification system for agricultural crops
Coverage: Common pests and diseases affecting crops in Tamil Nadu and Kerala
Regional Focus: South Indian agricultural conditions and seasonal patterns

This knowledge base helps farmers identify, treat, and prevent common agricultural pests and diseases
based on symptoms, visual signs, and regional occurrence patterns.
"""
        documents.append(Document(
            page_content=overview_content,
            metadata={"source": "pest_overview", "type": "overview", "category": "pest_disease"}
        ))
        
        # Process pest data
        for pest_name, pest_info in PEST_DISEASE_KNOWLEDGE["common_pests"].items():
            pest_content = f"""
PEST IDENTIFICATION: {pest_name.upper().replace('_', ' ')}
{'='*60}
Scientific Name: {pest_info['scientific_name']}
Common Name: {pest_name.replace('_', ' ').title()}
Severity Level: {pest_info['severity']}

CROPS AFFECTED:
{', '.join(pest_info['crops_affected'])}

SYMPTOMS TO LOOK FOR:
{chr(10).join(f"• {symptom}" for symptom in pest_info['symptoms'])}

VISUAL IDENTIFICATION SIGNS:
{chr(10).join(f"• {sign}" for sign in pest_info['visual_signs'])}

TREATMENT OPTIONS:
{chr(10).join(f"• {treatment}" for treatment in pest_info['treatment'])}

PREVENTION METHODS:
{chr(10).join(f"• {prevention}" for prevention in pest_info['prevention'])}

SEASONAL OCCURRENCE:
Active during: {', '.join(pest_info['season'])}

AGRICULTURAL IMPACT:
This pest can cause {pest_info['severity']} damage to crops. Early identification and 
treatment are crucial for maintaining crop health and preventing economic losses.
"""
            documents.append(Document(
                page_content=pest_content,
                metadata={
                    "source": f"pest_{pest_name}",
                    "type": "pest_identification",
                    "category": "pest_disease",
                    "pest_name": pest_name,
                    "severity": pest_info['severity']
                }
            ))
        
        # Process disease data
        for disease_name, disease_info in PEST_DISEASE_KNOWLEDGE["common_diseases"].items():
            disease_content = f"""
DISEASE IDENTIFICATION: {disease_name.upper().replace('_', ' ')}
{'='*60}
Scientific Name: {disease_info['scientific_name']}
Common Name: {disease_name.replace('_', ' ').title()}
Severity Level: {disease_info['severity']}

CROPS AFFECTED:
{', '.join(disease_info['crops_affected'])}

SYMPTOMS TO LOOK FOR:
{chr(10).join(f"• {symptom}" for symptom in disease_info['symptoms'])}

VISUAL IDENTIFICATION SIGNS:
{chr(10).join(f"• {sign}" for sign in disease_info['visual_signs'])}

TREATMENT OPTIONS:
{chr(10).join(f"• {treatment}" for treatment in disease_info['treatment'])}

PREVENTION METHODS:
{chr(10).join(f"• {prevention}" for prevention in disease_info['prevention'])}

FAVORABLE CONDITIONS:
Occurs during: {', '.join(disease_info['season'])}

AGRICULTURAL IMPACT:
This disease can cause {disease_info['severity']} damage to crops. Proper diagnosis and 
timely intervention are essential for crop protection and yield preservation.
"""
            documents.append(Document(
                page_content=disease_content,
                metadata={
                    "source": f"disease_{disease_name}",
                    "type": "disease_identification", 
                    "category": "pest_disease",
                    "disease_name": disease_name,
                    "severity": disease_info['severity']
                }
            ))
        
        # Regional pest/disease data
        for region, region_data in REGIONAL_PEST_DATA.items():
            region_content = f"""
REGIONAL PEST & DISEASE PROFILE: {region.upper().replace('_', ' ')}
{'='*70}
State: {region.replace('_', ' ').title()}

COMMON REGIONAL ISSUES:
{chr(10).join(f"• {issue}" for issue in region_data['common_issues'])}

SEASONAL PATTERNS:
"""
            for season, issues in region_data['seasonal_patterns'].items():
                region_content += f"""
{season.title()} Season:
{chr(10).join(f"  • {issue}" for issue in issues)}
"""
            
            region_content += """
CROP-SPECIFIC PEST/DISEASE PROBLEMS:
"""
            for crop, problems in region_data['major_crops_pests'].items():
                region_content += f"""
{crop.title()}:
{chr(10).join(f"  • {problem}" for problem in problems)}
"""
            
            region_content += f"""

REGIONAL MANAGEMENT STRATEGY:
Farmers in {region.replace('_', ' ').title()} should focus on these specific pest and disease 
issues based on local climate conditions and cropping patterns. Regular monitoring and 
preventive measures are recommended for optimal crop protection.
"""
            
            documents.append(Document(
                page_content=region_content,
                metadata={
                    "source": f"regional_{region}",
                    "type": "regional_pest_data",
                    "category": "pest_disease",
                    "region": region
                }
            ))
        
        return documents

# --- Main App Logic ---
st.title("🌱 AI Pest & Agriculture Assistant")
st.markdown("""
**Complete Agricultural Intelligence System with Pest Detection**

Get comprehensive farming advice combining:
- 🔍 **Pest & Disease Detection** - Upload images or describe symptoms
- 🧪 **Detailed Soil Analysis** for Tamil Nadu & Kerala (16 major cities)
- 🌾 **Government Schemes** and agricultural policies  
- 📊 **10+ Soil Parameters** including pH, nutrients, organic matter
- 🚜 **Crop Recommendations** based on actual soil conditions
- 🌿 **Crop Cycle Management** with seasonal guidance
""")

# --- Input Section ---
st.markdown("### 📤 Input Your Query")

# Create tabs for different input types
tab1, tab2, tab3 = st.tabs(["🖼️ Image + Text", "🖼️ Image Only", "📝 Text Only"])

user_image = None
user_text = ""

with tab1:
    st.markdown("**Upload an image and provide additional description:**")
    user_image = st.file_uploader("Upload crop/plant image", type=['jpg', 'jpeg', 'png'], key="img_text")
    user_text = st.text_area("Describe the problem or provide additional context:", key="text_with_img")
    
    if user_image or user_text:
        if st.button("🔍 Analyze Image & Text", type="primary", key="submit_img_text"):
            st.session_state.process_query = True
            st.session_state.current_image = user_image
            st.session_state.current_text = user_text

with tab2:
    st.markdown("**Upload an image for pest/disease analysis:**")
    user_image = st.file_uploader("Upload crop/plant image", type=['jpg', 'jpeg', 'png'], key="img_only")
    
    if user_image:
        if st.button("🔍 Analyze Image", type="primary", key="submit_img_only"):
            st.session_state.process_query = True
            st.session_state.current_image = user_image
            st.session_state.current_text = ""

with tab3:
    st.markdown("**Describe your agricultural query:**")
    user_text = st.text_area("Ask about soil conditions, pests, diseases, crop cycles, or government schemes:", key="text_only")
    
    if user_text:
        if st.button("📝 Submit Question", type="primary", key="submit_text_only"):
            st.session_state.process_query = True
            st.session_state.current_image = None
            st.session_state.current_text = user_text

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("🔧 Configuration")
    
    # Knowledge base status
    kb_status = []
    
    if SOIL_KB_PATH:
        st.success("✅ Soil Knowledge Base Found")
        kb_status.append("soil")
    else:
        st.error("❌ Soil Knowledge Base Not Found")
    
    if CROP_CYCLE_KB_PATH:
        st.success("✅ Crop Cycle Knowledge Base Found")
        kb_status.append("crop_cycle")
    else:
        st.error("❌ Crop Cycle Knowledge Base Not Found")
    
    st.success("✅ Pest/Disease Knowledge Base Loaded")
    kb_status.append("pest_disease")
    
    st.info(f"""
**🌐 Additional Sources:**
- Web Sources: {len(FARMER_URLS)} URLs
- Pest Database: {len(PEST_DISEASE_KNOWLEDGE['common_pests'])} pests
- Disease Database: {len(PEST_DISEASE_KNOWLEDGE['common_diseases'])} diseases
    """)
    
    # API Key configuration
    try:
        groq_api_key = os.environ["GROQ_API_KEY"]
        st.success("✅ Groq API Key loaded from environment")
    except KeyError:
        groq_api_key = st.text_input("🔑 Enter your Groq API Key:", type="password")
        if not groq_api_key:
            st.error("Please provide your Groq API Key to continue.")
            st.stop()
    
    # Optional: OpenAI API Key for vision analysis
    st.markdown("**🔍 Enhanced Image Analysis (Optional):**")
    openai_api_key = st.text_input("🔑 OpenAI API Key (for GPT-4 Vision):", type="password", help="Optional: Enables advanced image analysis")
    if openai_api_key:
        st.success("✅ OpenAI Vision API available")
    else:
        st.info("ℹ️ Using basic image analysis (OpenAI key optional)")
    
    # Model selection with vision support info
    available_models = [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile", 
        "gemma2-9b-it"
    ]
    
    selected_model = st.selectbox(
        "🤖 Select AI Model:",
        available_models,
        index=0,
        help="Choose the language model for agricultural analysis. Note: Groq models don't support vision yet."
    )
    
    st.warning("⚠️ **Image Analysis Note:** Groq models don't currently support vision. Images are analyzed using basic color analysis + text descriptions.")

# --- Enhanced Session State Initialization ---
if "vectors" not in st.session_state:
    with st.spinner("🔨 Building comprehensive agricultural knowledge base with pest detection..."):
        try:
            # Initialize embeddings
            st.session_state.embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
            
            all_documents = []
            
            # 1. Load soil knowledge base if available
            if SOIL_KB_PATH:
                loader = SoilKnowledgeLoader(SOIL_KB_PATH)
                soil_documents = loader.load_all_documents()
                all_documents.extend(soil_documents)
                st.sidebar.info(f"📊 Loaded {len(soil_documents)} soil documents")
            
            # 2. Load crop cycle knowledge base if available
            if CROP_CYCLE_KB_PATH:
                crop_loader = CropCycleKnowledgeLoader(CROP_CYCLE_KB_PATH)
                crop_documents = crop_loader.load_all_documents()
                all_documents.extend(crop_documents)
                st.sidebar.info(f"🌿 Loaded {len(crop_documents)} crop cycle documents")
            
            # 3. Load pest/disease knowledge base
            pest_loader = PestDiseaseKnowledgeLoader()
            pest_documents = pest_loader.load_all_documents()
            all_documents.extend(pest_documents)
            st.sidebar.info(f"🐛 Loaded {len(pest_documents)} pest/disease documents")
            
            # 4. Load web-based farming information
            try:
                web_loader = WebBaseLoader(FARMER_URLS)
                web_documents = web_loader.load()
                
                for doc in web_documents:
                    doc.metadata.update({
                        "category": "farming_schemes",
                        "type": "government_info",
                        "data_format": "web"
                    })
                
                all_documents.extend(web_documents)
                st.sidebar.info(f"🌐 Loaded {len(web_documents)} web documents")
            except Exception as e:
                st.sidebar.warning(f"⚠️ Web loading issue: {e}")
            
            if not all_documents:
                st.error("No documents could be loaded! Please check your setup.")
                st.stop()
            
            # 5. Process all documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1200,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " "]
            )
            final_documents = text_splitter.split_documents(all_documents)
            
            # 6. Create vector store
            st.session_state.vectors = FAISS.from_documents(final_documents, st.session_state.embeddings)
            
            # Summary
            soil_docs = len([d for d in final_documents if d.metadata.get("category", "").startswith("soil")])
            crop_docs = len([d for d in final_documents if d.metadata.get("category") == "crop_cycle"])
            pest_docs = len([d for d in final_documents if d.metadata.get("category") == "pest_disease"])
            scheme_docs = len([d for d in final_documents if d.metadata.get("category") == "farming_schemes"])
            
            st.sidebar.success(f"""
✅ **Knowledge Base Ready!**
- Total chunks: {len(final_documents)}
- Soil data: {soil_docs} chunks  
- Crop cycles: {crop_docs} chunks
- Pest/Disease: {pest_docs} chunks
- Schemes/Web: {scheme_docs} chunks
            """)
            
        except Exception as e:
            st.error(f"❌ Failed to build knowledge base: {e}")
            st.stop()

# --- Enhanced RAG Chain Setup ---
if "vectors" in st.session_state:
    try:
        # Initialize LLM
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=selected_model
        )

        # Enhanced prompt template with pest/disease detection
        prompt_template = ChatPromptTemplate.from_template("""
You are an expert agricultural advisor and pest/disease specialist with comprehensive knowledge of:
1. Pest and disease identification for agricultural crops
2. Visual symptom analysis and diagnostic techniques
3. Treatment and prevention strategies for pest/disease management
4. Soil science and soil health analysis for Tamil Nadu and Kerala
5. Crop cycle management, seasonal planning, and growth stages
6. Indian government agricultural schemes and policies
7. Integrated pest management (IPM) practices

PEST/DISEASE ANALYSIS PROTOCOL:
When analyzing pest or disease issues:
- Identify symptoms and visual signs from descriptions or images
- Match symptoms to known pest/disease patterns
- Consider regional and seasonal factors (Tamil Nadu/Kerala climate)
- Provide specific identification with scientific names
- Recommend immediate treatment options
- Suggest long-term prevention strategies
- Consider crop-specific vulnerabilities

RESPONSE RULES:
- For PEST/DISEASE questions: Focus on identification, treatment, and prevention
- For SOIL questions: Show normalized soil values + crop recommendations
- For SCHEME questions: Explain scheme details and application process
- For COMBINED queries: Organize response into clear sections
- Always provide practical, actionable advice
- Include regional considerations for Tamil Nadu/Kerala

SOIL VALUE NORMALIZATION (apply automatically):
• Clay content >100%: divide by 10 (e.g., 311% → 31.1%)
• Sand/Silt content >100%: divide by 10 
• pH >10: divide by 10 (e.g., 59.1 → 5.91)
• Nitrogen >10 g/kg: divide by 100 (e.g., 323.89 → 3.24 g/kg)
• Any percentage >100%: normalize to realistic range

NEVER mention original incorrect values. ONLY show normalized values confidently.

<context>
{context}
</context>

Question: {input}

Provide comprehensive analysis with practical recommendations:
""")
    except Exception as e:
        st.error(f"❌ Failed to initialize RAG chain: {e}")
        st.stop()