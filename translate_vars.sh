#!/bin/bash

# Check if source file path is provided
if [ $# -lt 1 ]; then
    echo "Usage: ./translate_vars.sh <source_file> [function_name]"
    echo "If function_name is provided, performs local analysis and translation"
    echo "If function_name is not provided, performs global analysis and translation"
    echo "Example (local): ./translate_vars.sh ./gzip/inflate.c huft_build"
    echo "Example (global): ./translate_vars.sh ./gzip/trees.c"
    exit 1
fi

SOURCE_FILE=$1
FUNCTION_NAME=$2
BASE_NAME=$(basename "$SOURCE_FILE" .c)
OUTPUT_DIR="./gzip"
TRANSLATION_OUTPUT_DIR="./results"
PROCESSED_FILE="$OUTPUT_DIR/processed_${BASE_NAME}.c"

if [ -n "$FUNCTION_NAME" ]; then
    # Local analysis and translation
    echo "Performing local analysis and translation for function: $FUNCTION_NAME"
    
    echo "Running local analysis..."
    python code_analyzer_local.py "$SOURCE_FILE" "$FUNCTION_NAME" \
        "$OUTPUT_DIR/definitions_output_${BASE_NAME}.txt" \
        "$OUTPUT_DIR/dfg_output_${BASE_NAME}.txt"

    echo "Running local translation..."
    python translate_local.py "$FUNCTION_NAME" \
        "$OUTPUT_DIR/definitions_output_${BASE_NAME}.txt" \
        "$OUTPUT_DIR/dfg_output_${BASE_NAME}.txt" \
        "$TRANSLATION_OUTPUT_DIR/translation_${BASE_NAME}.rs"
else
    # Global analysis and translation
    echo "Performing global analysis and translation"
    
    echo "Running global analysis..."
    python code_analyzer_global.py "$SOURCE_FILE" "$PROCESSED_FILE" \
        "$OUTPUT_DIR/definitions_output_${BASE_NAME}.txt" \
        "$OUTPUT_DIR/dfg_output_${BASE_NAME}.txt"

    echo "Running global translation..."
    python translate_global.py \
        "$OUTPUT_DIR/definitions_output_${BASE_NAME}.txt" \
        "$OUTPUT_DIR/dfg_output_${BASE_NAME}.txt" \
        "$TRANSLATION_OUTPUT_DIR/translation_${BASE_NAME}.rs"
fi

echo "Analysis and translation completed!"
