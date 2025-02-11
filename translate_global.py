import sys
import argparse
from openai import OpenAI
import os

def load_api_key():
    """Load OpenAI API key from environment variable"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found")
    return api_key

def read_file_content(file_path):
    """Read and return the content of a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {str(e)}")

def chat_with_gpt(definitions_text, dfg_text, prompt_template=None):
    """Send the definitions and DFG to GPT for translation"""
    try:
        client = OpenAI(api_key=load_api_key())
        
        if prompt_template is None:
            prompt_template = """
            Translate the C definitions into Rust code, following these rules:
            1. Create a state struct, and convert C variable definitions to Rust struct fields
            2. Create enum indicators for all pointer varibales being used as function parameters or struct fields in their corresponding DFGs, replace with enums to indicate the fields and avoid multiple mutable borrowing.
            
            Only return the translated code, with no additional explanations.
            """
        
        # Combine definitions and DFG with prompt template
        full_prompt = f"""
        The C definitions:
        {definitions_text}
        
        The Data Flow Graphs:
        {dfg_text}
        
        {prompt_template}
        """
        
        response = client.chat.completions.create(
            model="o1-2024-12-17",
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        raise Exception(f"Error in GPT translation: {str(e)}")

def write_output(content, output_file):
    """Write content to output file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        raise Exception(f"Error writing to {output_file}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(
        description='Translate C definitions to Rust using GPT-4'
    )
    parser.add_argument('definitions_file', 
                       help='Path to read the extracted definitions')
    parser.add_argument('dfg_file', 
                       help='Path to read the extracted DFG')
    parser.add_argument('translation_file', 
                       help='Path to save the GPT translation')
    parser.add_argument('--prompt', 
                       help='Path to custom prompt template file (optional)')
    args = parser.parse_args()

    try:
        print("Reading input files...")
        definitions_text = read_file_content(args.definitions_file)
        dfg_text = read_file_content(args.dfg_file)
        
        # Read custom prompt if provided
        prompt_template = None
        if args.prompt:
            prompt_template = read_file_content(args.prompt)
            print("Using custom prompt template")
        
        print("Sending to GPT for translation...")
        translation = chat_with_gpt(definitions_text, dfg_text, prompt_template)
        
        print("Writing translation to file...")
        write_output(translation, args.translation_file)
        
        print(f"\nTranslation completed successfully!")
        print(f"Results written to: {args.translation_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()