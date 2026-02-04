import mammoth

def docx2mark(file_path):
    """
    Read a .docx file and convert its content to Markdown format.
    
    Args:
        file_path (str): Path to the .docx file.
    
    Returns:
        str: The content of the document in Markdown format.
    """
    with open(file_path, "rb") as docx_file:
        result = mammoth.convert_to_markdown(docx_file)
        return result.value
