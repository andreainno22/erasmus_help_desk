import pdfplumber

def process_pdf_for_llm(input_pdf_path, output_txt_path):
    """
    Extracts tables from a PDF and converts them into a clean, structured
    text file that is easy for an LLM to read.
    """
    print(f"Starting processing for '{input_pdf_path}'...")
    full_structured_text = ""

    try:
        with pdfplumber.open(input_pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # extract_tables() returns a list of all tables found on a page
                tables = page.extract_tables()
                
                for table in tables:
                    # A table is a list of rows, and a row is a list of cells
                    for row in table:
                        # Clean up the row: remove None values and strip whitespace
                        cleaned_row = [
                            cell.replace('\n', ' ').strip() if cell is not None else "" 
                            for cell in row
                        ]
                        
                        # Join the cells with a clear separator
                        line = " | ".join(cleaned_row)
                        full_structured_text += line + "\n"
                
                print(f"Processed Page {i+1}/{len(pdf.pages)}")

        # Save the clean, structured text to an output file
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(full_structured_text)
            
        print(f"\n✅ Success! Clean data saved to '{output_txt_path}'")
        return full_structured_text

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return None

# --- RUN THE SCRIPT ---
if __name__ == "__main__":
    pdf_file = "data/esami_incoming_students/destinazioni_bando_unipi_2025-2026.pdf"
    clean_text_file = "destinazioni_LLM_ready.txt"
    
    process_pdf_for_llm(pdf_file, clean_text_file)