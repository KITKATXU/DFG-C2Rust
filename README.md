# C to Rust Variable Translator

This project focuses on translating C variables (both global and local) to Rust before handling the translation of computation and I/O code. It provides automated data flow analysis and variable declarations translation.

## Features

- Global variable translation
- Local variable translation within specific functions
- Data flow analysis for variable usage
- Automatic generation of Rust-equivalent structures

## Usage

### Translating Global Variables

To translate all global variables in a C file:

```bash
./translate_vars.sh ./gzip/trees.c
```

### Translating Local Variables

To translate local variables within a specific function:

```bash
./translate_vars.sh ./gzip/inflate.c huft_build
```

Note: You need to provide the function name as the second argument for local variable translation.

## Prerequisites

Before using this translator, you need to:

1. We are translating the project from:
```bash
git clone https://github.com/kunpengcompute/gzipC.git
```

2. Ensure you have the following dependencies installed:
- Python 3.8
- clang
- python-clang bindings

## Project Structure

- `code_analyzer_global.py`: Analyzes global variable definitions and usage
- `code_analyzer_local.py`: Analyzes local variable definitions and usage
- `translate_global.py`: Translates global variables to Rust
- `translate_local.py`: Translates local variables to Rust
- `translate_vars.sh`: Shell script to streamline the translation process

## Output

The translator generates:
- Rust enum definitions for C pointers
- Variable declarations with appropriate Rust types

## Note

This is a preprocessing step for C to Rust translation. The output should be reviewed and potentially modified before being used in the final Rust codebase.