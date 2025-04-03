def process_message(message):
    message = message.lower()
    
    # Greetings
    if any(word in message for word in ['hi', 'hello', 'hey']):
        return "Hello! I'm your file conversion assistant. How can I help you today?"
    
    # File conversion related
    elif any(word in message for word in ['convert', 'change', 'transform']):
        return "Sure! Please upload the file you want to convert and specify the format (e.g., 'to PDF')."
    
    # Help
    elif 'help' in message:
        return "I can help you convert between these formats: PDF, DOCX, JPG, PNG, and TXT. "\
               "Just upload a file and tell me what format you want!"
    
    # Goodbye
    elif any(word in message for word in ['bye', 'goodbye', 'exit']):
        return "Goodbye! Come back if you need more file conversions."
    
    # Default response
    else:
        return "I'm a file conversion bot. I can help you convert files between different formats. "\
               "Try uploading a file and telling me what format you want!"