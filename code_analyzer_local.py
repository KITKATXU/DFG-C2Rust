import clang.cindex
import argparse
import sys
import os
import re

def get_function_range(filename, function_name):
    """Get the start and end line numbers of the function"""
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    start_line = 0
    end_line = 0
    brace_count = 0
    in_function = False
    in_comment = False
    
    # Print potential function matches for debugging
    print("\nSearching for function definition...")
    # for i, line in enumerate(lines, 1):
    #     if function_name in line and '(' in line:
    #         print(f"Found potential match at line {i}: {line.strip()}")
    
    for i, line in enumerate(lines, 1):
        line_strip = line.strip()
        
        # Handle multi-line comments
        if '/*' in line_strip:
            in_comment = True
        if '*/' in line_strip:
            in_comment = False
            continue
        if in_comment or line_strip.startswith('//'):
            continue
            
        # Check function declaration start
        if not in_function:
            # Simple function declaration detection: function name followed by left parenthesis
            if line_strip.startswith(function_name + "(") and not line_strip.endswith(";"):
                start_line = i
                # print(start_line)
                in_function = True
                if '{' in line:
                    brace_count += line.count('{')
                continue
        
        # Count braces inside function
        if in_function:
            brace_count += line.count('{')
            brace_count -= line.count('}')
            
            if brace_count == 0 and '}' in line:
                end_line = i
                break
    
    if start_line == 0 or end_line == 0:
        raise ValueError(f"Function '{function_name}' not found in file")
    
    print(f"\nFunction range: lines {start_line}-{end_line}")
    return start_line, end_line

def extract_function_variables(filename, function_name):
    """Extract variables and their uses within the function range"""
    index = clang.cindex.Index.create()
    
    # Get function range
    func_start, func_end = get_function_range(filename, function_name)
    
    # Set compilation options
    args = [
        '-x', 'c',  # Specify language as C
        '-std=c99',  # Use C99 standard
        '-I/usr/include',  # System include paths
        '-I/usr/local/include',
        '-I.',  # Current directory
        '-I..',  # Parent directory
        '-D__USE_GNU',
        '-D_GNU_SOURCE'
    ]
    
    # Parse file
    tu = index.parse(filename, args=args)
    
    # Read file content
    with open(filename, 'r') as f:
        file_lines = f.readlines()
    
    variables_info = {
        'parameters': [],
        'locals': []
    }
    
    dfg_info = {}
    function_node = None
    
    # Find target function
    for node in tu.cursor.get_children():
        if (node.kind == clang.cindex.CursorKind.FUNCTION_DECL and 
            node.is_definition() and 
            node.spelling == function_name):
            function_node = node
            break
    
    if not function_node:
        raise ValueError(f"Function '{function_name}' not found")
    
    def get_definition_line(line_num):
        """Get the complete definition line"""
        if 0 < line_num <= len(file_lines):
            return file_lines[line_num - 1].strip()
        return ""
    
    def is_in_function_range(line_num):
        """Check if a line number is within the function range"""
        return func_start <= line_num <= func_end
    
    def process_variable(node, is_param=False):
        """Process a variable declaration"""
        if not is_param and not is_in_function_range(node.location.line):
            return
            
        var_info = {
            'name': node.spelling,
            'type': node.type.spelling,
            'line': node.location.line,
            'code': get_definition_line(node.location.line)
        }
        
        if is_param:
            variables_info['parameters'].append(var_info)
        else:
            variables_info['locals'].append(var_info)
        
        dfg_info[node.spelling] = {
            'type': node.type.spelling,
            'definition': {
                'line': node.location.line,
                'code': var_info['code']
            },
            'uses': []
        }
    
    def find_references(cursor):
        """Find all references to variables within function range"""
        # Process current node
        if cursor.kind == clang.cindex.CursorKind.PARM_DECL:
            process_variable(cursor, is_param=True)
        elif cursor.kind == clang.cindex.CursorKind.VAR_DECL:
            if is_in_function_range(cursor.location.line):
                process_variable(cursor, is_param=False)
        elif cursor.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
            if (cursor.spelling in dfg_info and 
                is_in_function_range(cursor.location.line)):
                use_line = get_definition_line(cursor.location.line)
                dfg_info[cursor.spelling]['uses'].append({
                    'line': cursor.location.line,
                    'code': use_line
                })
        
        # Process child nodes
        if cursor.kind == clang.cindex.CursorKind.COMPOUND_STMT:
            # Special handling for function body
            for child in cursor.get_children():
                if child.location.file and child.location.file.name == filename:
                    find_references(child)
        else:
            # Handle other nodes
            for child in cursor.get_children():
                if child.location.file and child.location.file.name == filename:
                    if is_in_function_range(child.location.line):
                        find_references(child)
    
    # Analyze function body
    find_references(function_node)
    
    return variables_info, dfg_info

def write_variables_output(variables_info, output_file, function_name):
    """Write variables information to output file"""
    with open(output_file, 'w') as f:
        f.write(f"Variables in function: {function_name}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Function Parameters:\n")
        f.write("-" * 40 + "\n")
        if variables_info['parameters']:
            for param in sorted(variables_info['parameters'], key=lambda x: x['line']):
                f.write(f"\nLine {param['line']}: {param['name']}\n")
                f.write(f"Type: {param['type']}\n")
                f.write(f"```c\n{param['code']}\n```\n")
        else:
            f.write("None\n")
        
        f.write("\nLocal Variables:\n")
        f.write("-" * 40 + "\n")
        if variables_info['locals']:
            for var in sorted(variables_info['locals'], key=lambda x: x['line']):
                f.write(f"\nLine {var['line']}: {var['name']}\n")
                f.write(f"Type: {var['type']}\n")
                f.write(f"```c\n{var['code']}\n```\n")
        else:
            f.write("None\n")

def write_dfg_output(dfg_info, output_file, function_name):
    """Write DFG information to output file"""
    with open(output_file, 'w') as f:
        f.write(f"Data Flow Graph for function: {function_name}\n")
        f.write("=" * 80 + "\n\n")
        
        for var_name, info in dfg_info.items():
            f.write(f"Variable: {var_name}\n")
            f.write(f"Type: {info['type']}\n")
            f.write("\nDefinition:\n")
            f.write(f"Line {info['definition']['line']}:\n")
            f.write(f"```c\n{info['definition']['code']}\n```\n")
            
            f.write("\nUses:\n")
            if info['uses']:
                for i, use in enumerate(sorted(info['uses'], key=lambda x: x['line']), 1):
                    f.write(f"\n{i}. Line {use['line']}:\n")
                    f.write(f"```c\n{use['code']}\n```\n")
            else:
                f.write("No uses found\n")
            
            f.write("\n" + "=" * 40 + "\n\n")

def main():
    parser = argparse.ArgumentParser(
        description='Extract local variables and parameters from a C function'
    )
    parser.add_argument('input_file', help='Path to the input C source file')
    parser.add_argument('function_name', help='Name of the function to analyze')
    parser.add_argument('vars_output', help='Path to save the variables information')
    parser.add_argument('dfg_output', help='Path to save the DFG information')
    args = parser.parse_args()

    try:
        # Extract variables and create DFG
        variables_info, dfg_info = extract_function_variables(
            args.input_file, 
            args.function_name
        )
        
        # Write outputs
        write_variables_output(variables_info, args.vars_output, args.function_name)
        write_dfg_output(dfg_info, args.dfg_output, args.function_name)
        
        # Print summary
        total_params = len(variables_info['parameters'])
        total_locals = len(variables_info['locals'])
        print(f"\nExtraction completed. Found {total_params} parameters and {total_locals} local variables.")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()