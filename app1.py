import streamlit as st
import json
import base64
from pathlib import Path
import re
from datetime import datetime

def extract_pdf_metadata(filename: str) -> tuple[str, str, str]:
    """Extract country code, month, and year from filename."""
    pattern = r"([A-Z]{3})_forecast_(\w+)_(\d{4})\.pdf"
    match = re.match(pattern, filename, re.IGNORECASE)
    
    if match:
        country_code = match.group(1).upper()
        month = match.group(2).lower()
        year = match.group(3)
        return country_code, month, year
    else:
        return None, None, None

def display_pdf(pdf_file):
    """Display PDF using object tag - more Chrome compatible."""
    try:
        # Reset file pointer
        pdf_file.seek(0)
        base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        # Try object tag first (more compatible than iframe)
        pdf_display = f"""
        <object data="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="800px">
            <p>Votre navigateur ne peut pas afficher le PDF. 
            <a href="data:application/pdf;base64,{base64_pdf}" target="_blank">Cliquez ici pour l'ouvrir dans un nouvel onglet.</a></p>
        </object>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erreur lors de l'affichage du PDF: {str(e)}")
        # Fallback to download button
        pdf_file.seek(0)
        st.download_button(
            label="📄 Télécharger le PDF",
            data=pdf_file.read(),
            file_name=pdf_file.name,
            mime="application/pdf"
        )

def get_annotations_filename(annotator_name: str) -> str:
    """Generate filename with annotator name and date."""
    date_str = datetime.now().strftime("%Y%m%d")
    clean_name = re.sub(r'[^\w\-_]', '', annotator_name.lower())
    return f"{clean_name}_{date_str}.json"

def load_annotations_file(filename: str) -> list:
    """Load existing annotations from file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def save_annotation_to_dataset(annotator: str, country: str, month: str, year: str, summary: str, filename: str):
    """Add annotation to the dataset JSON file."""
    annotations = load_annotations_file(filename)
    
    new_annotation = {
        "annotator": annotator,
        "country": country,
        "month": month,
        "year": year,
        "summary": summary
    }
    
    annotations.append(new_annotation)
    
    with open(filename, 'w') as f:
        json.dump(annotations, f, indent=2)
    
    return filename

def main():
    st.set_page_config(page_title="Interface d'Annotation PDF - App 1", layout="wide")
    st.title("Interface d'Annotation de Prévisions de Conflits - App 1")
    
    # Initialize session state for annotations
    if 'session_annotations' not in st.session_state:
        st.session_state.session_annotations = []
    if 'annotator_name' not in st.session_state:
        st.session_state.annotator_name = ""
    if 'annotations_filename' not in st.session_state:
        st.session_state.annotations_filename = ""
    
    annotator_name = st.text_input(
        "Nom de l'Annotateur :",
        value=st.session_state.annotator_name,
        placeholder="Entrez votre nom"
    )
    st.session_state.annotator_name = annotator_name
    
    if not annotator_name:
        st.warning("Veuillez entrer votre nom d'annotateur pour continuer.")
        return
    
    # Generate filename for this annotator
    if not st.session_state.annotations_filename:
        st.session_state.annotations_filename = get_annotations_filename(annotator_name)
    
    annotations_file = st.session_state.annotations_filename
    
    # PDF upload
    uploaded_file = st.file_uploader(
        "Télécharger un Rapport PDF",
        type="pdf",
        help="Glissez-déposez un fichier PDF ou cliquez pour parcourir"
    )
    
    if uploaded_file is not None:
        # Extract metadata from filename
        country, month, year = extract_pdf_metadata(uploaded_file.name)
        
        if not all([country, month, year]):
            st.error(f"Impossible d'analyser le nom de fichier : {uploaded_file.name}")
            st.error("Format attendu : PAYS_forecast_mois_année.pdf (ex: NER_forecast_march_2026.pdf)")
            return
        
        # Display metadata
        st.success(f"Chargé : {country} - {month.title()} {year}")
        
        # Create two columns for layout
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.header("Document PDF")
            display_pdf(uploaded_file)
        
        with col2:
            st.header("Annotation")
            
            # Text input for summary
            summary = st.text_area(
                "Résumé :",
                height=300,
                placeholder="Entrez votre résumé du rapport de prévision de conflit...",
                key=f"summary_{country}_{month}_{year}"
            )
            
            # Submit button
            if st.button("Soumettre l'Annotation", type="primary"):
                if summary.strip():
                    try:
                        save_annotation_to_dataset(
                            annotator_name, country, month, year, summary, annotations_file
                        )
                        
                        # Add to session state for display
                        annotation_data = {
                            "annotator": annotator_name,
                            "country": country,
                            "month": month,
                            "year": year,
                            "summary": summary
                        }
                        st.session_state.session_annotations.append(annotation_data)
                        
                        st.success(f"Annotation sauvegardée dans {annotations_file}!")
                        
                        # Clear the current summary text area
                        del st.session_state[f"summary_{country}_{month}_{year}"]
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erreur lors de la sauvegarde de l'annotation : {str(e)}")
                else:
                    st.warning("Veuillez entrer un résumé avant de soumettre.")
            
            # Display current session annotations
            if st.session_state.session_annotations:
                st.subheader("Vos Annotations de Cette Session")
                st.json(st.session_state.session_annotations)
                
                # Show download section in sidebar only after user has annotations
                st.sidebar.header("Téléchargement du Jeu de Données")
                current_annotations = load_annotations_file(annotations_file)
                st.sidebar.write(f"Total d'annotations : {len(current_annotations)}")
                st.sidebar.write(f"Fichier : {annotations_file}")
                
                # Convert to JSON string for download
                json_str = json.dumps(current_annotations, indent=2)
                
                st.sidebar.download_button(
                    label="Télécharger Vos Annotations",
                    data=json_str,
                    file_name=annotations_file,
                    mime="application/json"
                )

if __name__ == "__main__":
    main()