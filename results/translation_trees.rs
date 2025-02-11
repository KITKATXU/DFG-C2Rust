/////////////////////////////////////////////
// Type Aliases
/////////////////////////////////////////////
type OffT = i64; // C's off_t
type Ulg = u32; // C's 'unsigned long' or similar
type Ush = u16; // C's 'unsigned short'
type Uch = u8;  // C's 'unsigned char'

/////////////////////////////////////////////
// Enums
/////////////////////////////////////////////
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum FileType {
    Unknown,
    Binary,
    Ascii,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum FileMethod {
    Deflate,
    Store,
}

// Enums to replace pointer usage in tree_desc
#[derive(Clone, Copy)]
pub enum TreePointer {
    DynLtree,
    DynDtree,
    BlTree,
    StaticLtree,
    StaticDtree,
    None,
}

#[derive(Clone, Copy)]
pub enum ExtraBitsPointer {
    ExtraLBits,
    ExtraDBits,
    ExtraBLBits,
    None,
}

/////////////////////////////////////////////
// Struct Definitions
/////////////////////////////////////////////
#[derive(Clone, Copy)]
pub struct CtData {
    // Corresponds to the union fields in C
    pub freq: Ush,
    pub code: Ush,
    pub dad: Ush,
    pub len: Ush,
}

#[derive(Clone, Copy)]
pub struct TreeDesc {
    // Each pointer in C is replaced by an enum
    pub dyn_tree: TreePointer,
    pub static_tree: TreePointer,
    pub extra_bits: ExtraBitsPointer,
    pub extra_base: i32,
    pub elems: i32,
    pub max_length: i32,
    pub max_code: i32,
}

/////////////////////////////////////////////
// State Struct
/////////////////////////////////////////////
pub struct State {
    // Converted from C's global arrays/variables:
    pub extra_lbits: [i32; 29],
    pub extra_dbits: [i32; 30],
    pub extra_blbits: [i32; 19],
    pub dyn_ltree: [CtData; 573],
    pub dyn_dtree: [CtData; 61],
    pub static_ltree: [CtData; 288],
    pub static_dtree: [CtData; 30],
    pub bl_tree: [CtData; 39],

    pub l_desc: TreeDesc,
    pub d_desc: TreeDesc,
    pub bl_desc: TreeDesc,

    pub bl_count: [Ush; 16],
    pub bl_order: [Uch; 19],
    pub heap: [i32; 573],
    pub heap_len: i32,
    pub heap_max: i32,
    pub depth: [Uch; 573],

    pub length_code: [Uch; 256],
    pub dist_code: [Uch; 512],
    pub base_length: [i32; 29],
    pub base_dist: [i32; 30],

    pub flag_buf: [Uch; 4096],
    pub last_lit: u32,
    pub last_dist: u32,
    pub last_flags: u32,
    pub flags: Uch,
    pub flag_bit: Uch,

    pub opt_len: Ulg,
    pub static_len: Ulg,
    pub compressed_len: OffT,
    pub input_len: OffT,

    pub file_type: FileType,
    pub file_method: FileMethod,

    pub block_start: i64,
    pub strstart: u32,
}