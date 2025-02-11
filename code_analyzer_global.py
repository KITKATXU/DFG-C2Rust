import clang.cindex
import sys
import argparse

def compress_multiline_code(lines):
    result = []
    i = 0
    while i < len(lines):
        current_line = lines[i].rstrip('\n')
        current_line_strip = current_line.strip()
        
        # Skip empty lines and comments
        if not current_line_strip or current_line_strip.startswith('//') or current_line_strip.startswith('/*'):
            result.append(current_line)
            i += 1
            continue
            
        # Check for line continuation
        if current_line_strip.endswith('\\'):
            combined_line = current_line_strip[:-1]
            j = i + 1
            while j < len(lines) and lines[j].strip().endswith('\\'):
                combined_line += ' ' + lines[j].strip()[:-1]
                j += 1
            if j < len(lines):
                combined_line += ' ' + lines[j].strip()
            result.append(combined_line)
            i = j + 1
        # Check for assignment continuation
        elif current_line_strip.endswith('='):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not next_line.startswith('//'):
                    result.append(f"{current_line_strip} {next_line}")
                    i += 2
                    continue
            result.append(current_line)
            i += 1
        else:
            result.append(current_line)
            i += 1
    
    return '\n'.join(result)

def extract_globals_with_usage(filename):
    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    
    with open(filename, 'r') as f:
        file_lines = f.readlines()
    
    function_ranges = {}
    
    for node in tu.cursor.get_children():
        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            if node.is_definition():
                start_line = node.extent.start.line
                end_line = node.extent.end.line
                function_ranges[node.spelling] = {
                    'start': start_line,
                    'end': end_line,
                    'code': '\n'.join(file_lines[start_line-1:end_line])
                }
    
    dfg_info = {}
    
    for node in tu.cursor.get_children():
        if node.kind == clang.cindex.CursorKind.VAR_DECL:
            if not node.location.is_in_system_header and node.location.file and node.location.file.name == filename:
                var_name = node.spelling
                def_line = file_lines[node.location.line - 1].strip()
                dfg_info[var_name] = {
                    'type': node.type.spelling,
                    'definition': {
                        'file': node.location.file.name,
                        'line': node.location.line,
                        'code': def_line
                    },
                    'uses': []
                }
        elif node.kind == clang.cindex.CursorKind.STRUCT_DECL:
            if not node.location.is_in_system_header:
                struct_name = "struct " + node.spelling
                struct_lines = []
                start_line = node.extent.start.line - 1
                end_line = node.extent.end.line
                for i in range(start_line, end_line):
                    struct_lines.append(file_lines[i].strip())
                
                dfg_info[struct_name] = {
                    'type': 'struct',
                    'definition': {
                        'file': node.location.file.name,
                        'line': node.location.line,
                        'code': '\n'.join(struct_lines)
                    },
                    'uses': []
                }
    
    def find_references(cursor):
        for node in cursor.get_children():
            if node.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
                if node.spelling in dfg_info:
                    line_num = node.location.line
                    containing_function = None
                    function_code = None
                    for func_name, range_info in function_ranges.items():
                        if range_info['start'] <= line_num <= range_info['end']:
                            containing_function = func_name
                            function_code = range_info['code']
                            break
                    
                    use_line = file_lines[line_num - 1].strip()
                    dfg_info[node.spelling]['uses'].append({
                        'file': node.location.file.name,
                        'line': line_num,
                        'code': use_line,
                        'function': containing_function or "global scope",
                        'function_code': function_code or use_line
                    })
            find_references(node)
    
    find_references(tu.cursor)
    return dfg_info

def extract_all_definitions(filename):
    index = clang.cindex.Index.create()
    tu = index.parse(filename)
    
    with open(filename, 'r') as f:
        file_lines = f.readlines()
    
    definitions = {
        'macros': [],
        'globals': [],
        'structs': [],
        'enums': []
    }
    
    def get_complete_definition(start_line, end_line):
        return ''.join(file_lines[start_line-1:end_line]).strip()
    
    for node in tu.cursor.get_children():
        if node.location.file and node.location.file.name != filename:
            continue
            
        if node.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
            macro_def = {
                'name': node.spelling,
                'line': node.location.line,
                'code': file_lines[node.location.line-1].strip()
            }
            definitions['macros'].append(macro_def)
            
        elif node.kind == clang.cindex.CursorKind.VAR_DECL:
            if not node.location.is_in_system_header:
                var_def = {
                    'name': node.spelling,
                    'type': node.type.spelling,
                    'line': node.location.line,
                    'code': file_lines[node.location.line-1].strip()
                }
                definitions['globals'].append(var_def)
                
        elif node.kind == clang.cindex.CursorKind.STRUCT_DECL:
            if not node.location.is_in_system_header and node.is_definition():
                struct_def = {
                    'name': node.spelling,
                    'line': node.extent.start.line,
                    'code': get_complete_definition(
                        node.extent.start.line,
                        node.extent.end.line
                    )
                }
                definitions['structs'].append(struct_def)
                
        elif node.kind == clang.cindex.CursorKind.ENUM_DECL:
            if not node.location.is_in_system_header and node.is_definition():
                enum_def = {
                    'name': node.spelling,
                    'line': node.extent.start.line,
                    'code': get_complete_definition(
                        node.extent.start.line,
                        node.extent.end.line
                    )
                }
                definitions['enums'].append(enum_def)
    
    return definitions

def write_dfg_output(dfg_info, output_file):
    with open(output_file, 'w') as f:
        f.write("Data Flow Graph for Global Variables and Structs:\n")
        for name, info in dfg_info.items():
            f.write(f"\n{'='*50}\n")
            f.write(f"Variable/Struct: {name}\n")
            f.write(f"Type: {info['type']}\n")
            f.write("\nDefinition:\n")
            f.write(f"```c\n{info['definition']['code']}\n```\n")
            
            if info['uses']:
                f.write("\nUsages:\n")
                for i, use in enumerate(info['uses'], 1):
                    f.write(f"\n{i}. Function: {use['function']}\n")
                    f.write(f"Usage code:\n")
                    f.write(f"```c\n{use['code']}\n```\n")
            else:
                f.write("\nNo usages found.\n")
            f.write(f"{'='*50}\n")

def write_definitions_output(definitions, output_file):
    with open(output_file, 'w') as f:
        f.write("=== Macro Definitions ===\n\n")
        for macro in sorted(definitions['macros'], key=lambda x: x['line']):
            f.write(f"Line {macro['line']}: {macro['name']}\n")
            f.write(f"```c\n{macro['code']}\n```\n\n")
        
        f.write("\n=== Global Variables ===\n\n")
        for var in sorted(definitions['globals'], key=lambda x: x['line']):
            f.write(f"Line {var['line']}: {var['name']} ({var['type']})\n")
            f.write(f"```c\n{var['code']}\n```\n\n")
        
        f.write("\n=== Struct Definitions ===\n\n")
        for struct in sorted(definitions['structs'], key=lambda x: x['line']):
            f.write(f"Line {struct['line']}: {struct['name']}\n")
            f.write(f"```c\n{struct['code']}\n```\n\n")
        
        f.write("\n=== Enum Definitions ===\n\n")
        for enum in sorted(definitions['enums'], key=lambda x: x['line']):
            f.write(f"Line {enum['line']}: {enum['name']}\n")
            f.write(f"```c\n{enum['code']}\n```\n\n")

def main():
    parser = argparse.ArgumentParser(
        description='Analyze C source files: compress multiline code, extract definitions and generate DFG'
    )
    parser.add_argument('input_file', help='Path to the input C source file')
    parser.add_argument('compressed_file', help='Path to save the compressed code')
    parser.add_argument('dfg_output', help='Path to save the DFG analysis')
    parser.add_argument('definitions_output', help='Path to save the extracted definitions')
    args = parser.parse_args()

    try:
        # First compress the code
        print("Compressing multiline code...")
        with open(args.input_file, 'r') as f:
            original_code = f.readlines()
        compressed_code = compress_multiline_code(original_code)
        
        # Save compressed code
        with open(args.compressed_file, 'w') as f:
            f.write(compressed_code)
        print(f"Compressed code written to: {args.compressed_file}")
        
        # Extract DFG information from compressed code
        print("\nExtracting DFG information...")
        dfg_info = extract_globals_with_usage(args.compressed_file)
        write_dfg_output(dfg_info, args.dfg_output)
        print(f"DFG analysis written to: {args.dfg_output}")
        
        # Extract all definitions
        print("\nExtracting definitions...")
        definitions = extract_all_definitions(args.compressed_file)
        write_definitions_output(definitions, args.definitions_output)
        
        # Print summary
        total_defs = sum(len(defs) for defs in definitions.values())
        print(f"\nExtraction completed successfully. Found:")
        print(f"- {len(definitions['macros'])} macro definitions")
        print(f"- {len(definitions['globals'])} global variables")
        print(f"- {len(definitions['structs'])} struct definitions")
        print(f"- {len(definitions['enums'])} enum definitions")
        print(f"\nTotal: {total_defs} definitions")
        print(f"Definitions written to: {args.definitions_output}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()