import streamlit as st
import os
import json
import base64
import requests
from pathlib import Path
from PIL import Image
import io
import difflib
import time

# Set page configuration
st.set_page_config(
    page_title="AI Agricultural Pest Identification",
    page_icon="🐛",
    layout="wide"
)
# Add custom CSS for fixed image sizes
st.markdown("""
    <style>
    /* Fix sample image preview sizes */
    [data-testid="column"] img {
        height: 200px !important;
        object-fit: cover !important;
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

# Constants
GROQ_API_KEY = st.secrets['groq']
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
MODEL = 'meta-llama/llama-4-scout-17b-16e-instruct'

# Knowledge base paths - check multiple possible locations
POSSIBLE_PEST_KB_PATHS = [
    "../Pests-knowledgebase/pests-data.json",
    "Pests-knowledgebase/pests-data.json",
    "./Pests-knowledgebase/pests-data.json", 
    "Pest-knowledgebase/pests-data.json",
    "./Pest-knowledgebase/pests-data.json", 
    "../Pest-knowledgebase/pests-data.json",
    "pests-data.json",
    "./pests-data.json",
    "Pests-knowledgebase\\pests-data.json",
    ".\\Pests-knowledgebase\\pests-data.json"
]

# Find the correct pest KB path
PEST_KB_PATH = None
for path in POSSIBLE_PEST_KB_PATHS:
    if os.path.exists(path):
        PEST_KB_PATH = path
        break

class PestKnowledgeLoader:
    """Enhanced loader for pest knowledge base with smart matching"""
    
    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        self.pest_data = None
        self.pest_names = []
        self.all_symptoms = []
        self.all_crops = []
        
    def load_pest_data(self):
        """Load pest data from JSON file and create lookup structures"""
        try:
            if self.kb_path.exists():
                with open(self.kb_path, 'r', encoding='utf-8') as f:
                    self.pest_data = json.load(f)
                
                # Extract pest info for matching
                if 'pests' in self.pest_data and isinstance(self.pest_data['pests'], list):
                    for pest in self.pest_data['pests']:
                        if isinstance(pest, dict):
                            # Extract pest names
                            name = pest.get('pestName', '')
                            common_names = pest.get('commonNames', [])
                            self.pest_names.extend([name] + common_names)
                            
                            # Extract symptoms
                            symptoms = pest.get('damageSymptoms', [])
                            if isinstance(symptoms, list):
                                self.all_symptoms.extend(symptoms)
                            
                            # Extract crops
                            crops = pest.get('hostPlantsCrops', [])
                            if isinstance(crops, list):
                                self.all_crops.extend(crops)
                
                return True
            else:
                st.sidebar.error(f"Pest knowledge base not found at: {self.kb_path}")
                return False
        except Exception as e:
            st.sidebar.error(f"Error loading pest knowledge base: {e}")
            return False
    
    def find_matching_pests(self, text_input=""):
        """Find pests that match user input (location, crop, symptoms)"""
        if not self.pest_data or 'pests' not in self.pest_data:
            return []
        
        text_input = text_input.lower()
        matching_pests = []
        
        for pest in self.pest_data['pests']:
            if not isinstance(pest, dict):
                continue
                
            match_score = 0
            match_reasons = []
            
            # Check location match
            states = pest.get('statesRegions', [])
            for state in states:
                if state.lower() in text_input:
                    match_score += 3
                    match_reasons.append(f"Found in {state}")
            
            # Check crop match
            crops = pest.get('hostPlantsCrops', [])
            for crop in crops:
                if crop.lower() in text_input:
                    match_score += 2
                    match_reasons.append(f"Affects {crop}")
            
            # Check symptom match
            symptoms = pest.get('damageSymptoms', [])
            for symptom in symptoms:
                if any(word in text_input for word in symptom.lower().split()):
                    match_score += 1
                    match_reasons.append(f"Symptom: {symptom}")
            
            # Check common names
            common_names = pest.get('commonNames', [])
            for name in common_names:
                if name.lower() in text_input:
                    match_score += 2
                    match_reasons.append(f"Common name: {name}")
            
            if match_score > 0:
                matching_pests.append({
                    'pest': pest,
                    'score': match_score,
                    'reasons': match_reasons
                })
        
        # Sort by match score
        matching_pests.sort(key=lambda x: x['score'], reverse=True)
        return matching_pests[:5]  # Return top 5 matches

    def get_enhanced_pest_context(self, additional_text=""):
        """Convert pest data to enhanced context string emphasizing KB data"""
        if not self.pest_data:
            return ""
        
        # Find matching pests based on additional text
        matching_pests = self.find_matching_pests(additional_text)
        
        context = """=== AUTHORITATIVE PEST KNOWLEDGE BASE ===
THIS DATABASE CONTAINS VERIFIED, REGION-SPECIFIC PEST INFORMATION FOR INDIAN AGRICULTURE.
ALWAYS PRIORITIZE AND REFERENCE THIS DATA OVER GENERAL KNOWLEDGE.

"""
        
        # Add high-priority matching pests first
        if matching_pests:
            context += "🎯 HIGH-PRIORITY MATCHES BASED ON USER CONTEXT:\n\n"
            for match in matching_pests:
                pest = match['pest']
                context += self._format_pest_info(pest, is_priority=True)
                context += f"MATCH REASONS: {', '.join(match['reasons'])}\n"
                context += "-" * 80 + "\n\n"
        
        # Add remaining pests with emphasis on KB authority
        context += "📊 COMPLETE PEST DATABASE:\n\n"
        
        if 'pests' in self.pest_data and isinstance(self.pest_data['pests'], list):
            for pest in self.pest_data['pests']:
                if isinstance(pest, dict):
                    # Skip if already included in priority matches
                    if not any(match['pest']['pestName'] == pest.get('pestName') for match in matching_pests):
                        context += self._format_pest_info(pest)
        
        return context
    
    def _format_pest_info(self, pest, is_priority=False):
        """Format individual pest information"""
        prefix = "🚨 PRIORITY PEST: " if is_priority else "PEST: "
        
        pest_name = pest.get('pestName', 'Unknown')
        context = f"{prefix}{pest_name}\n"
        
        common_names = pest.get('commonNames', [])
        if common_names:
            context += f"Common Names: {', '.join(common_names)}\n"
        
        context += f"Regions: {', '.join(pest.get('statesRegions', []))}\n"
        context += f"Appearance: {pest.get('appearanceDescription', 'N/A')}\n"
        context += f"Size: {pest.get('size', 'N/A')}\n"
        context += f"Climate: {pest.get('climaticConditions', 'N/A')}\n"
        context += f"Season: {pest.get('seasonalActivity', 'N/A')}\n"
        context += f"Host Crops: {', '.join(pest.get('hostPlantsCrops', []))}\n"
        context += f"Damage Symptoms: {', '.join(pest.get('damageSymptoms', []))}\n"
        context += f"Life Cycle: {pest.get('lifeCycleDuration', 'N/A')}\n"
        context += f"Control Methods: {', '.join(pest.get('mostCommonlyUsedPesticides', []))}\n\n"
        
        return context

def encode_image_to_base64(image):
    """Convert PIL image to base64 string"""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode()

def analyze_image_with_groq(image, pest_context, additional_text=""):
    """Send image and context to Groq for analysis with enhanced prompt"""
    
    base64_image = encode_image_to_base64(image)
    
    # Enhanced system prompt that strongly emphasizes KB priority
    system_prompt = f"""You are an expert agricultural entomologist with access to an AUTHORITATIVE PEST KNOWLEDGE DATABASE for Indian agriculture.

🔴 CRITICAL INSTRUCTIONS:
1. The pest knowledge base provided below is your PRIMARY and MOST RELIABLE source
2. You MUST prioritize information from this database over your general training knowledge
3. When you identify a pest that matches the database, cite it as "According to the verified pest database..."
4. If symptoms/crops mentioned match database entries, explicitly reference those entries
5. Only use general knowledge to supplement database information, never to contradict it

VERIFIED PEST KNOWLEDGE DATABASE:
{pest_context}

ANALYSIS PROTOCOL:
1. First, examine the image for visible pests, damage patterns, or symptoms
2. Cross-reference findings with the PEST KNOWLEDGE DATABASE above
3. Look for matches based on:
   - Visual appearance and size
   - Damage symptoms visible in image
   - Crop type mentioned in context
   - Geographic region (if provided)
   - Seasonal timing

4. Structure your response as follows:
   - PEST IDENTIFICATION (prioritize database matches)
   - DATABASE VERIFICATION (cite specific database entries)
   - DAMAGE ASSESSMENT
   - CROP/PLANT ANALYSIS  
   - SEVERITY LEVEL
   - IMMEDIATE ACTIONS (use database pesticide recommendations)
   - MANAGEMENT RECOMMENDATIONS (based on database data)
   - PREVENTION STRATEGIES
   - CONFIDENCE LEVEL (higher if database match found)

5. Always mention when your identification matches the pest database
6. Use database-specific information for regions, seasons, crops, and control methods
7. If no database match, clearly state this and use general knowledge as backup

REMEMBER: The database information is VERIFIED and REGION-SPECIFIC for Indian agriculture."""

    user_message = "Please analyze this agricultural image for pest identification. Prioritize information from the pest knowledge database provided in the system prompt."
    
    if additional_text.strip():
        user_message += f"\n\nAdditional Context: {additional_text}"
        user_message += "\n\nIMPORTANT: Look for pests in the database that match the region, crops, or symptoms mentioned in this context."

    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text",
                        "text": user_message
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
        "max_tokens": 2500,
        "temperature": 0.1  # Lower temperature for more consistent database usage
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"Error calling Groq API: {str(e)}"
    except KeyError as e:
        return f"Error parsing response: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def main():
    st.title("🐛 AI Agricultural Pest Identification System")
    st.markdown("""
    **Advanced Pest Detection & Management Assistant**
    
    Upload an image of your crop, plant, or suspected pest damage to get:
    - 🔍 **Accurate Pest Identification** using verified Indian pest database
    - 📊 **Region-Specific Information** from local agricultural data  
    - 🎯 **Database-Verified Treatment Recommendations** 
    - 🛡️ **Location-Based Prevention Strategies**
    - 🌱 **Integrated Pest Management** approaches
    """)

    # Sidebar for system status
    with st.sidebar:
        st.header("🔧 System Status")
        
        # Load pest knowledge base
        if PEST_KB_PATH:
            pest_loader = PestKnowledgeLoader(PEST_KB_PATH)
            kb_loaded = pest_loader.load_pest_data()
            
            if kb_loaded:
                st.success("✅ Verified Pest Database Loaded")
                st.code(f"Path: {PEST_KB_PATH}")
                
                # Display KB statistics
                if 'pests' in pest_loader.pest_data:
                    pest_count = len(pest_loader.pest_data['pests'])
                    st.info(f"📊 Verified Pest Records: {pest_count}")
                    
                    # Show unique regions covered
                    regions = set()
                    for pest in pest_loader.pest_data['pests']:
                        if isinstance(pest, dict):
                            regions.update(pest.get('statesRegions', []))
                    st.info(f"🗺️ Regions Covered: {len(regions)}")
            else:
                st.error("❌ Error Loading Pest Database")
        else:
            kb_loaded = False
            pest_loader = PestKnowledgeLoader("")
            st.error("❌ Pest Database Not Found")
            st.info("🧠 Will use general knowledge only (less accurate)")
        
        # API Status
        if GROQ_API_KEY:
            st.success("✅ AI Analysis Ready")
            st.info(f"🤖 Model: {MODEL}")

    # Main interface
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📷 Image Upload")
        
        uploaded_file = st.file_uploader(
            "Upload crop/plant image for pest analysis:",
            type=['png', 'jpg', 'jpeg'],
            help="Upload clear images showing plant damage, pests, or suspicious symptoms"
        )
        st.markdown("### Or choose a sample image:")
        sample_images = {
            "Busseola fusca on Maize": {"url":"https://raw.githubusercontent.com/surgehackathon-bit/SIH-Agri-2/refs/heads/master/samples/Busseola%20fusca%20on%20Maize.jpg",'prompt':"Growing maize crop in Palakkad, Kerala"},
            "Yellow Sugarcane Aphid": {"url":"https://raw.githubusercontent.com/surgehackathon-bit/SIH-Agri-2/refs/heads/master/samples/Yellow%20Sugarcane%20Aphid.jpg",'prompt':"Having sugarcane farm in Idukki, Kerala"},
            "Leaf Spots on Banana Leaf": {"url":"https://raw.githubusercontent.com/surgehackathon-bit/SIH-Agri-2/refs/heads/master/samples/Leaf%20Spots%20on%20Banana%20Leaf.jpg",'prompt':"Cultivating Banana trees in Thrissur and Thiruvananthapuram, Kerala"},
            "White spots on Rubber Plant": {"url":"https://raw.githubusercontent.com/surgehackathon-bit/SIH-Agri-2/refs/heads/master/samples/White%20spots%20on%20Rubber%20Plant.jpg",'prompt':"Growing Rubber plants for production in Kottayam, Kerala"}
        }

        cols = st.columns(len(sample_images))
        selected_sample = None
        
        for idx, (name, data) in enumerate(sample_images.items()):
            with cols[idx]:
                st.image(data["url"], caption=name, use_container_width=True)
                if st.button(f"Use this", key=f"example_tab1_{idx}"):
                    selected_sample = (name, data["url"], data["prompt"])
                    # Immediately update session state
                    st.session_state.selected_example_tab1 = selected_sample
                    st.session_state.selected_prompt = data["prompt"]
                    st.rerun()  # Force rerun to update the text area

        image = None
        if uploaded_file is not None:
            # User uploaded image
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image")
            st.info(f"📏 Image Size: {image.size[0]}x{image.size[1]} pixels")

        elif selected_sample is not None:
            st.success(f"✅ Selected: {selected_sample[0]}")

        # Check if we have a selected sample from previous interaction
        if image is None and 'selected_example_tab1' in st.session_state:
            selected_sample = st.session_state.selected_example_tab1
            try:
                response = requests.get(selected_sample[1], timeout=10)
                response.raise_for_status()  # Raise an error for bad status codes
                
                # Verify we got image content
                content_type = response.headers.get('content-type', '')
                if 'image' not in content_type:
                    st.error(f"URL did not return an image (got {content_type})")
                else:
                    image = Image.open(io.BytesIO(response.content))
                    # Convert to RGB if necessary (some images might be in RGBA or other modes)
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    st.image(image, caption=f"Selected: {selected_sample[0]}", use_container_width=False, width=400)
                    st.info(f"📏 Image Size: {image.size[0]}x{image.size[1]} pixels")
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching image from URL: {e}")
            except Exception as e:
                st.error(f"Error loading sample image: {e}")

    with col2:
        st.header("📝 Context Information")
        
        if 'selected_prompt' not in st.session_state:
            st.session_state.selected_prompt = ''
        
        additional_text = st.text_area(
            "Location, Crop & Symptom Details:",
            value=st.session_state.selected_prompt,
            height=150,
            placeholder="""Provide specific details to match with pest database:
        ...
🗺️ LOCATION (Important for database matching):
• State/Region: "Kerala", "Tamil Nadu", "Karnataka", etc.

🌾 CROP TYPE:
• Specific crop: "rice", "cotton", "tomato", "citrus", etc.

🔍 SYMPTOMS OBSERVED:
• "yellowing leaves", "holes in leaves", "wilting plants"
• "brown spots", "leaf rolling", "stunted growth"
• "white powdery coating", "sticky honeydew", etc.

📅 TIMING:
• Growth stage: "flowering", "fruiting", "seedling"  
• Season: "monsoon", "summer", "winter crop"

This information helps match against our verified pest database for accurate identification.""",
            key="context_input"
        )
        
        # Show database preview based on context
        if kb_loaded and additional_text.strip():
            with st.expander("🎯 Database Matches Preview"):
                matches = pest_loader.find_matching_pests(additional_text)
                if matches:
                    st.success(f"Found {len(matches)} potential matches in database!")
                    for match in matches[:3]:  # Show top 3
                        pest = match['pest']
                        st.write(f"**{pest.get('pestName')}** (Score: {match['score']})")
                        st.write(f"Regions: {', '.join(pest.get('statesRegions', []))}")
                        st.write(f"Crops: {', '.join(pest.get('hostPlantsCrops', []))}")
                else:
                    st.info("No specific matches found - will use general database")

    # Analysis section - moved processing status above the button
    if image is not None:
        st.header("🧠 Pest Analysis")
        
        # Show processing status ABOVE the button
        st.markdown("### 📋 Processing Status:")
        col_status1, col_status2 = st.columns(2)
        
        with col_status1:
            st.info("✅ **Image:** Ready for analysis")
            if additional_text.strip():
                st.success(f"✅ **Context:** {len(additional_text)} characters")
            else:
                st.warning("⚠️ **Context:** Consider adding location/crop info for better database matching")
        
        with col_status2:
            if kb_loaded:
                matches = pest_loader.find_matching_pests(additional_text)
                if matches:
                    st.success(f"✅ **Database:** {len(matches)} potential matches found")
                else:
                    st.info("ℹ️ **Database:** General database will be used")
            else:
                st.error("❌ **Database:** Not available")
        
        # Analyze button
        analyze_button = st.button("🔍 Analyze Image with Pest Database", type="primary", use_container_width=True)
        
        if analyze_button:
            with st.spinner("🔬 Analyzing image with verified pest database..."):
                try:
                    # Start timing
                    start_time = time.time()
                    
                    # Get enhanced pest context
                    pest_context = pest_loader.get_enhanced_pest_context(additional_text) if kb_loaded else ""
                    
                    # Analyze image
                    result = analyze_image_with_groq(image, pest_context, additional_text)
                    
                    # Calculate response time
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    # Display results
                    st.markdown("### 🎯 Analysis Results:")
                    st.markdown(result)
                    
                    # Show response time
                    st.markdown("---")
                    col_time1, col_time2, col_time3 = st.columns(3)
                    with col_time1:
                        st.metric("⏱️ Response Time", f"{response_time:.2f} seconds")
                    with col_time2:
                        if kb_loaded:
                            matches = pest_loader.find_matching_pests(additional_text)
                            st.metric("🎯 DB Matches", len(matches))
                        else:
                            st.metric("🎯 DB Matches", "N/A")
                    with col_time3:
                        st.metric("📊 Analysis Status", "✅ Complete")
                    
                    # Show database usage summary
                    if kb_loaded:
                        matches = pest_loader.find_matching_pests(additional_text)
                        if matches:
                            st.success(f"✅ Analysis completed using verified pest database with {len(matches)} targeted matches!")
                        else:
                            st.info("ℹ️ Analysis completed using general pest database.")
                    else:
                        st.warning("⚠️ Analysis completed without pest database - results may be less accurate.")
                    
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")

    # Information sections
    with st.expander("🗃️ What's in Our Pest Database?"):
        if kb_loaded and 'pests' in pest_loader.pest_data:
            pests = pest_loader.pest_data['pests']
            
            # Extract unique values for display
            all_states = set()
            all_crops = set()
            pest_types = set()
            
            for pest in pests:
                if isinstance(pest, dict):
                    all_states.update(pest.get('statesRegions', []))
                    all_crops.update(pest.get('hostPlantsCrops', []))
                    if pest.get('pestName'):
                        pest_types.add(pest['pestName'])
            
            col_db1, col_db2 = st.columns(2)
            with col_db1:
                st.markdown("**📍 Geographic Coverage:**")
                st.write(f"States/Regions: {len(all_states)}")
                st.write("Including: " + ", ".join(sorted(list(all_states))[:8]) + "...")
                
                st.markdown("**🌾 Crop Coverage:**") 
                st.write(f"Host Crops: {len(all_crops)}")
                st.write("Including: " + ", ".join(sorted(list(all_crops))[:8]) + "...")
            
            with col_db2:
                st.markdown(f"**🐛 Total Pest Species: {len(pest_types)}**")
                st.markdown("**Database Features:**")
                st.write("✅ Regional distribution data")
                st.write("✅ Crop-specific host information") 
                st.write("✅ Damage symptom descriptions")
                st.write("✅ Seasonal activity patterns")
                st.write("✅ Verified control methods")
        else:
            st.error("Database not loaded - showing general information only")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    🐛 Enhanced AI Agricultural Pest Identification System<br>
    Powered by Verified Indian Pest Database + Advanced Vision AI
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
