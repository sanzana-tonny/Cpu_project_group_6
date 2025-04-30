import sys
import re

# --- MIPS Instruction Data ---

# Register mapping: Name -> 5-bit binary string
registers = {
    "$zero": "00000", "$0": "00000",
    "$at": "00001", "$1": "00001",
    "$v0": "00010", "$2": "00010", "$v1": "00011", "$3": "00011",
    "$a0": "00100", "$4": "00100", "$a1": "00101", "$5": "00101",
    "$a2": "00110", "$6": "00110", "$a3": "00111", "$7": "00111",
    "$t0": "01000", "$8": "01000", "$t1": "01001", "$9": "01001",
    "$t2": "01010", "$10": "01010", "$t3": "01011", "$11": "01011",
    "$t4": "01100", "$12": "01100", "$t5": "01101", "$13": "01101",
    "$t6": "01110", "$14": "01110", "$t7": "01111", "$15": "01111",
    "$s0": "10000", "$16": "10000", "$s1": "10001", "$17": "10001",
    "$s2": "10010", "$18": "10010", "$s3": "10011", "$19": "10011",
    "$s4": "10100", "$20": "10100", "$s5": "10101", "$21": "10101",
    "$s6": "10110", "$22": "10110", "$s7": "10111", "$23": "10111",
    "$t8": "11000", "$24": "11000", "$t9": "11001", "$25": "11001",
    "$k0": "11010", "$26": "11010", "$k1": "11011", "$27": "11011",
    "$gp": "11100", "$28": "11100",
    "$sp": "11101", "$29": "11101",
    "$fp": "11110", "$30": "11110",
    "$ra": "11111", "$31": "11111",
}

# R-Type instructions: mnemonic -> funct code (opcode is 000000)
r_type_instructions = {
    "add": "100000", "addu": "100001", "sub": "100010", "subu": "100011",
    "and": "100100", "or": "100101", "xor": "100110", "nor": "100111",
    "slt": "101010", "sltu": "101011",
    "sll": "000000", "srl": "000010", "sra": "000011",
    "jr": "001000", "jalr": "001001",
    "mult": "011000", "multu": "011001", "div": "011010", "divu": "011011",
    "mfhi": "010000", "mflo": "010010",
    "syscall": "001100", # Syscall technically R-type format
}

# I-Type instructions: mnemonic -> opcode
i_type_instructions = {
    "addi": "001000", "addiu": "001001", "andi": "001100", "ori": "001101",
    "xori": "001110", "lui": "001111", "slti": "001010", "sltiu": "001011",
    "beq": "000100", "bne": "000101",
    "lw": "100011", "sw": "101011",
    "lb": "100000", "lbu": "100100", "lh": "100001", "lhu": "100101",
    "sb": "101000", "sh": "101001",
    "blez": "000110",  # <-- ADDED BLEZ
}

# J-Type instructions: mnemonic -> opcode
j_type_instructions = {
    "j": "000010", "jal": "000011",
}

# --- Helper Functions ---

def clean_line(line):
    """Removes comments and leading/trailing whitespace."""
    line = line.split('#', 1)[0] # Remove comments
    return line.strip()

def decimal_to_binary(n, bits):
    """Converts a decimal integer n to a binary string of 'bits' bits."""
    if isinstance(n, str): # Handle hex strings like '0x100'
        try:
            # Allow labels to be passed if they are already resolved numbers, else handle later
            if n in symbol_table:
                 n = symbol_table[n] # Use resolved address if it's a label
            else:
                 n = int(n, 0) # Try to parse as number (handles dec/hex/oct)
        except ValueError:
            raise ValueError(f"Invalid immediate value or unresolved label: {n}")
        except KeyError:
             raise ValueError(f"Undefined label used as immediate: {n}")

    if not isinstance(n, int): # Ensure we have an integer after potential label lookup
        raise ValueError(f"Cannot convert non-integer value to binary: {n}")

    if n >= 0:
        # Positive number or zero
        s = bin(n)[2:] # Remove '0b' prefix
        if len(s) > bits:
            # Allow truncation for jump addresses (handled specifically later)
            if bits != 26:
                print(f"Warning: Value {n} (0x{n:x}) truncated to fit {bits} bits.", file=sys.stderr)
            return s[-bits:].zfill(bits) # Take lower bits and pad
        return s.zfill(bits) # Pad with leading zeros
    else:
        # Negative number (two's complement)
        # Check if the negative number is representable
        min_val = -(2**(bits-1))
        max_val = (2**(bits-1)) - 1
        if n < min_val :
             raise ValueError(f"Value {n} too small for {bits} bits (signed, range {min_val} to {max_val})")
        # Compute the positive equivalent in 2's complement
        val = (1 << bits) + n
        s = bin(val)[2:]
        # Return the correct number of bits, zfilled if needed
        return s.zfill(bits)


def parse_operands(ops_str):
    """Parses comma-separated operands, handling imm(reg) format."""
    # --- MODIFIED ---
    if not ops_str or ops_str.isspace(): # If the string is None, empty or only whitespace
        return []           # Return an empty list immediately
    # --- END MODIFIED ---

    ops = []
    # Regex to handle 'imm(reg)' format correctly without splitting imm
    # It splits by comma, unless the comma is inside parentheses
    for part in re.split(r",\s*(?![^()]*\))", ops_str):
        cleaned_part = part.strip()
        if cleaned_part: # Avoid adding empty strings if there are trailing commas etc.
            ops.append(cleaned_part)
    return ops

def parse_mem_operand(op):
    """Parses 'imm(reg)' or 'label(reg)' format, returns (imm/label, reg)."""
    match = re.match(r"([\w\d_.-]+)\s*\(\s*(\$\w+|\$\d+)\s*\)", op) # Allow hex/decimal/labels in immediate, numeric registers
    if match:
        return match.group(1), match.group(2)
    # Handle case where offset is missing -> assume 0
    match_no_offset = re.match(r"\(\s*(\$\w+|\$\d+)\s*\)", op)
    if match_no_offset:
        return "0", match_no_offset.group(1) # Return offset 0
    # Maybe just a label (for la pseudo-instruction)
    if op in symbol_table:
        return op, None
    raise ValueError(f"Invalid memory operand format: {op}")

# --- Assembler Logic ---

symbol_table = {} # Label -> Address
data_symbol_table = {} # Data Label -> Address
base_address_text = 0x00400000 # Standard MIPS text segment start
base_address_data = 0x10010000 # Standard MIPS data segment start
current_address = base_address_text
in_text_section = True # Start in .text by default

def pass_one(lines):
    """First pass: build symbol table and calculate addresses."""
    global current_address, in_text_section, base_address_text, symbol_table, data_symbol_table
    # Reset global state for potentially multiple runs
    symbol_table = {}
    data_symbol_table = {}
    pc = base_address_text # Program counter simulation for text segment
    data_pc = base_address_data # Address counter for data segment
    in_text_section = True

    print("--- Pass One: Building Symbol Table ---")
    for line_num, line in enumerate(lines, 1):
        cleaned = clean_line(line)
        if not cleaned:
            continue # Skip empty lines and comments

        # Check for section directives first
        if cleaned.lower() == ".data": # Make directive check case-insensitive
            in_text_section = False
            print(f"  Line {line_num}: Switched to .data section")
            continue
        elif cleaned.lower() == ".text": # Make directive check case-insensitive
            in_text_section = True
            current_address = pc # Track address in text segment
            print(f"  Line {line_num}: Switched to .text section")
            continue

        # Check for labels (handle labels ending with :)
        match = re.match(r"^\s*([a-zA-Z_]\w*):\s*(.*)", cleaned) # More robust label regex
        label = None
        instruction_part = cleaned
        if match:
            label = match.group(1)
            instruction_part = match.group(2).strip()

            # --- Label Definition Handling ---
            current_label_addr = data_pc if not in_text_section else pc
            if label in symbol_table or label in data_symbol_table:
                print(f"Error line {line_num}: Label '{label}' already defined.", file=sys.stderr)
                # Continue processing but this is an error state
            else:
                if in_text_section:
                    symbol_table[label] = current_label_addr
                    print(f"  Line {line_num}: Found text label '{label}' at address 0x{current_label_addr:08x}")
                else:
                    data_symbol_table[label] = current_label_addr
                    print(f"  Line {line_num}: Found data label '{label}' at address 0x{current_label_addr:08x}")
            # --- End Label Definition Handling ---


        if not instruction_part:
             continue # Skip lines with only labels

        # Process based on section to calculate addresses
        parts = instruction_part.split(None, 1)
        opcode_or_directive = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""

        if in_text_section:
            # Simulate PC increment for instructions in text section
            # Handle pseudo-instructions that expand to multiple instructions
            if opcode_or_directive == "li":
                 # Check immediate size - might only need one instruction (ori)
                 # This requires parsing the immediate value here, which is complex for pass 1
                 # Simplification: Assume worst case (lui+ori) for address calculation
                 pc += 8
            elif opcode_or_directive == "la":
                 pc += 8 # lui + ori (or lui + move)
            elif opcode_or_directive == "move":
                 pc += 4 # Usually one 'addu'
            elif opcode_or_directive == "nop":
                 pc += 4 # Represents one instruction
            elif opcode_or_directive in r_type_instructions or \
                 opcode_or_directive in i_type_instructions or \
                 opcode_or_directive in j_type_instructions:
                pc += 4 # Most instructions take 4 bytes
            else:
                 # Unknown instruction or directive in .text, ignore for PC calc
                 # Error will be caught in pass two
                 pass
        else:
            # Handle data directives in data section to advance data_pc
            if opcode_or_directive == ".word":
                num_words = len(args_str.split(','))
                data_pc += 4 * num_words
                # print(f"  Line {line_num}: Found .word directive, size {4 * num_words}, next data addr 0x{data_pc:08x}")
            elif opcode_or_directive == ".space":
                try:
                    size = int(args_str.strip())
                    data_pc += size
                    # print(f"  Line {line_num}: Found .space directive, size {size}, next data addr 0x{data_pc:08x}")
                except ValueError:
                     print(f"Error line {line_num}: Invalid size for .space: {args_str}", file=sys.stderr)
            elif opcode_or_directive == ".asciiz":
                match_str = re.search(r'"(.*)"', args_str)
                if match_str:
                    # Handle escaped quotes correctly if needed, basic version:
                    processed_string = match_str.group(1).encode('utf-8').decode('unicode_escape')
                    size = len(processed_string) + 1 # +1 for null terminator
                    data_pc += size
                    # print(f"  Line {line_num}: Found .asciiz directive, size {size}, next data addr 0x{data_pc:08x}")
                else:
                     print(f"Error line {line_num}: Invalid string for .asciiz: {args_str}", file=sys.stderr)
            elif opcode_or_directive == ".ascii":
                 match_str = re.search(r'"(.*)"', args_str)
                 if match_str:
                     processed_string = match_str.group(1).encode('utf-8').decode('unicode_escape')
                     size = len(processed_string)
                     data_pc += size
                    # print(f"  Line {line_num}: Found .ascii directive, size {size}, next data addr 0x{data_pc:08x}")
                 else:
                     print(f"Error line {line_num}: Invalid string for .ascii: {args_str}", file=sys.stderr)
            elif opcode_or_directive == ".byte":
                 num_bytes = len(args_str.split(','))
                 data_pc += num_bytes
                 # print(f"  Line {line_num}: Found .byte directive, size {num_bytes}, next data addr 0x{data_pc:08x}")
            elif opcode_or_directive == ".align":
                 try:
                     align_val = int(args_str.strip())
                     if align_val < 0: raise ValueError("Alignment must be non-negative")
                     align_bytes = 2**align_val
                     offset = (align_bytes - (data_pc % align_bytes)) % align_bytes
                     data_pc += offset
                     # print(f"  Line {line_num}: Found .align directive {align_val}, adding {offset} bytes, next data addr 0x{data_pc:08x}")
                 except ValueError as e:
                      print(f"Error line {line_num}: Invalid value for .align: {args_str} ({e})", file=sys.stderr)
            # Add other data directives (.byte, .half, .float, .double, .align) if needed

    print(f"--- Pass One Complete. Final text PC: 0x{pc:08x}, Final data PC: 0x{data_pc:08x} ---")
    print("Symbol Table:", symbol_table)
    print("Data Symbol Table:", data_symbol_table)
    # Combine symbol tables for easier lookup in pass two
    symbol_table.update(data_symbol_table)


def pass_two(lines):
    """Second pass: generate machine code."""
    global current_address, in_text_section, base_address_text
    machine_code = []
    current_address = base_address_text # Reset for pass two address calculation
    in_text_section = True # Assume starting in .text
    error_occurred = False # Flag to track errors

    print("\n--- Pass Two: Generating Machine Code ---")
    for line_num, line in enumerate(lines, 1):
        cleaned = clean_line(line)
        if not cleaned:
            continue

        if cleaned.lower() == ".data": # Make directive check case-insensitive
            in_text_section = False
            continue
        elif cleaned.lower() == ".text": # Make directive check case-insensitive
            in_text_section = True
            # We need to find the *actual* address of the first instruction after .text
            # This requires slightly smarter pass 1 or lookahead, but for now, assume
            # current_address tracking is roughly correct if code follows immediately.
            # A better approach would store addresses per line in pass 1.
            continue

        if not in_text_section:
            continue # Only assemble .text section

        # Strip label definitions for instruction parsing
        instruction_part = re.sub(r"^\s*[a-zA-Z_]\w*:\s*", "", cleaned).strip() # Use same robust regex
        if not instruction_part:
            continue # Skip lines with only labels

        # Get the address assigned in Pass 1 if possible, otherwise use tracked address
        # Simple tracking for now: instr_address is the address before processing this line
        instr_address = current_address

        parts = instruction_part.split(None, 1)
        opcode_mnem = parts[0].lower()
        ops_str = parts[1] if len(parts) > 1 else ""

        # Handle parsing operands after getting the mnemonic
        try:
             operands = parse_operands(ops_str)
        except Exception as e:
             print(f"Error parsing operands line {line_num} ('{instruction_part}'): {e}", file=sys.stderr)
             error_occurred = True
             current_address += 4 # Assume error takes space to avoid address cascade
             continue # Skip assembly for this line

        binary_instr = None
        instrs_generated = 0 # How many instructions were generated for this line

        try:
            # --- Handle NOP first as it's special ---
            if opcode_mnem == "nop":
                if len(operands) != 0: raise ValueError("nop takes 0 operands")
                # nop is sll $zero, $zero, 0
                binary_instr = "00000000000000000000000000000000"
                instrs_generated = 1

            # R-Type
            elif opcode_mnem in r_type_instructions:
                funct = r_type_instructions[opcode_mnem]
                rs, rt, rd, shamt = "00000", "00000", "00000", "00000"
                opcode = "000000"

                if opcode_mnem in ["add", "addu", "sub", "subu", "and", "or", "xor", "nor", "slt", "sltu"]:
                    if len(operands) != 3: raise ValueError("Expected 3 operands (rd, rs, rt)")
                    rd = registers[operands[0]]
                    rs = registers[operands[1]]
                    rt = registers[operands[2]]
                elif opcode_mnem in ["sll", "srl", "sra"]:
                    # Check if it's the specific NOP case (sll $0,$0,0)
                    if opcode_mnem == "sll" and operands[0] in ["$zero", "$0"] and operands[1] in ["$zero", "$0"] and int(operands[2]) == 0:
                         binary_instr = "00000000000000000000000000000000"
                    else:
                        if len(operands) != 3: raise ValueError("Expected 3 operands (rd, rt, shamt)")
                        rd = registers[operands[0]]
                        rt = registers[operands[1]]
                        shamt = decimal_to_binary(int(operands[2]), 5)
                        rs = "00000"
                elif opcode_mnem == "jr":
                    if len(operands) != 1: raise ValueError("Expected 1 operand (rs)")
                    rs = registers[operands[0]]
                elif opcode_mnem == "jalr":
                     if len(operands) == 1:
                         rs = registers[operands[0]]
                         rd = registers["$ra"]
                     elif len(operands) == 2:
                         rd = registers[operands[0]]
                         rs = registers[operands[1]]
                     else: raise ValueError("Expected 1 or 2 operands (rs) or (rd, rs)")
                     rt = "00000"
                elif opcode_mnem in ["mult", "multu", "div", "divu"]:
                    if len(operands) != 2: raise ValueError("Expected 2 operands (rs, rt)")
                    rs = registers[operands[0]]
                    rt = registers[operands[1]]
                elif opcode_mnem in ["mfhi", "mflo"]:
                     if len(operands) != 1: raise ValueError("Expected 1 operand (rd)")
                     rd = registers[operands[0]]
                elif opcode_mnem == "syscall":
                     # Check added by modifying parse_operands, just need to assemble
                     if len(operands) != 0: raise ValueError(f"Syscall takes 0 operands, got {len(operands)}")
                     # Correct format was already handled
                     binary_instr = f"{opcode}{rs}{rt}{rd}{shamt}{funct}"

                if binary_instr is None: # Assemble if not already done (e.g. syscall, specific sll)
                    binary_instr = f"{opcode}{rs}{rt}{rd}{shamt}{funct}"
                instrs_generated = 1

            # I-Type
            elif opcode_mnem in i_type_instructions:
                opcode = i_type_instructions[opcode_mnem]
                rs, rt, imm_val_or_label = "00000", "00000", "0" # Default immediate

                if opcode_mnem in ["addi", "addiu", "andi", "ori", "xori", "slti", "sltiu"]:
                    if len(operands) != 3: raise ValueError("Expected 3 operands (rt, rs, imm)")
                    rt = registers[operands[0]]
                    rs = registers[operands[1]]
                    imm_val_or_label = operands[2]
                    imm = decimal_to_binary(imm_val_or_label, 16)
                elif opcode_mnem == "lui":
                    if len(operands) != 2: raise ValueError("Expected 2 operands (rt, imm)")
                    rt = registers[operands[0]]
                    imm_val_or_label = operands[1]
                    imm = decimal_to_binary(imm_val_or_label, 16)
                elif opcode_mnem in ["lw", "sw", "lb", "lbu", "lh", "lhu", "sb", "sh"]:
                    if len(operands) != 2: raise ValueError("Expected 2 operands (rt, offset(rs))")
                    rt = registers[operands[0]]
                    offset_or_label, rs_reg = parse_mem_operand(operands[1])
                    rs = registers[rs_reg]
                    # We can resolve data labels here using the combined symbol table
                    imm = decimal_to_binary(offset_or_label, 16) # Handles numbers, hex, or resolved labels
                elif opcode_mnem in ["beq", "bne", "blez"]: # Added blez
                    # Format: op $rs, $rt, label  OR  blez $rs, label
                    expected_ops = 3 if opcode_mnem != "blez" else 2
                    if len(operands) != expected_ops: raise ValueError(f"Expected {expected_ops} operands")

                    rs = registers[operands[0]]
                    # rt is 0 for blez, otherwise the second register
                    rt = registers[operands[1]] if opcode_mnem != "blez" else "00000"
                    label = operands[-1] # Label is always the last operand

                    if label not in symbol_table: raise ValueError(f"Label '{label}' not found")
                    target_addr = symbol_table[label]
                    offset = (target_addr - (instr_address + 4)) >> 2
                    imm = decimal_to_binary(offset, 16)
                # --- Construct final I-type instruction ---
                binary_instr = f"{opcode}{rs}{rt}{imm}"
                instrs_generated = 1

            # J-Type
            elif opcode_mnem in j_type_instructions:
                opcode = j_type_instructions[opcode_mnem]
                if len(operands) != 1: raise ValueError("Expected 1 operand (label)")
                label = operands[0]
                if label not in symbol_table: raise ValueError(f"Label '{label}' not found")
                target_addr = symbol_table[label]
                jump_target = (target_addr & 0x0FFFFFFF) >> 2
                address = decimal_to_binary(jump_target, 26)
                binary_instr = f"{opcode}{address}"
                instrs_generated = 1

            # --- Pseudo-Instructions ---
            elif opcode_mnem == "move":
                 if len(operands) != 2: raise ValueError("Expected 2 operands (rt, rs)")
                 rt = registers[operands[0]]
                 rs = registers[operands[1]]
                 # addu $rt, $rs, $zero
                 binary_instr = f"000000{rs}{registers['$zero']}{rt}00000{r_type_instructions['addu']}"
                 instrs_generated = 1

            elif opcode_mnem == "li":
                if len(operands) != 2: raise ValueError("Expected 2 operands (rt, immediate)")
                rt = registers[operands[0]]
                imm_text = operands[1]
                try:
                    imm_val = int(imm_text, 0) # Handles dec/hex/oct immediate
                except ValueError: raise ValueError(f"Invalid immediate value for li: {imm_text}")

                # Optimization: Use single ORI if possible
                if 0 <= imm_val <= 0xFFFF:
                     opcode = i_type_instructions["ori"]
                     rs = registers["$zero"]
                     imm = decimal_to_binary(imm_val, 16)
                     binary_instr = f"{opcode}{rs}{rt}{imm}"
                     instrs_generated = 1
                else:
                     # lui $at, upper_16_bits
                     # ori $rt, $at, lower_16_bits
                     upper = (imm_val >> 16) & 0xFFFF
                     lower = imm_val & 0xFFFF

                     opcode_lui = i_type_instructions["lui"]
                     imm_lui = decimal_to_binary(upper, 16)
                     instr1 = f"{opcode_lui}00000{registers['$at']}{imm_lui}"
                     machine_code.append((instr_address, instr1))
                     print(f"  Line {line_num} (li expansion): 0x{instr_address:08x} -> {instr1} (lui)")
                     instrs_generated = 1 # First instruction generated

                     opcode_ori = i_type_instructions["ori"]
                     imm_ori = decimal_to_binary(lower, 16)
                     binary_instr = f"{opcode_ori}{registers['$at']}{rt}{imm_ori}"
                     # This second instruction will be added below, and PC incremented
                     instrs_generated = 2 # Second instruction will be generated

            elif opcode_mnem == "la":
                if len(operands) != 2: raise ValueError("Expected 2 operands (rt, label)")
                rt = registers[operands[0]]
                label = operands[1]
                if label not in symbol_table: raise ValueError(f"Label '{label}' not found")
                addr = symbol_table[label]
                upper = (addr >> 16) & 0xFFFF
                lower = addr & 0xFFFF

                # lui $at, upper_16_bits
                opcode_lui = i_type_instructions["lui"]
                imm_lui = decimal_to_binary(upper, 16)
                instr1 = f"{opcode_lui}00000{registers['$at']}{imm_lui}"
                machine_code.append((instr_address, instr1))
                print(f"  Line {line_num} (la expansion): 0x{instr_address:08x} -> {instr1} (lui)")
                instrs_generated = 1

                # ori $rt, $at, lower_16_bits (only needed if lower bits are non-zero)
                if lower != 0:
                     opcode_ori = i_type_instructions["ori"]
                     imm_ori = decimal_to_binary(lower, 16)
                     binary_instr = f"{opcode_ori}{registers['$at']}{rt}{imm_ori}"
                else: # If lower is 0, use move (addu)
                     binary_instr = f"000000{registers['$at']}{registers['$zero']}{rt}00000{r_type_instructions['addu']}"
                instrs_generated = 2


            else:
                # Check if it's a directive we should ignore in pass two
                if not opcode_mnem.startswith('.'):
                    raise ValueError(f"Unknown instruction mnemonic: '{opcode_mnem}'")
                # Otherwise ignore directives like .text, .data in pass two

            # --- Add generated instruction(s) and update address ---
            if binary_instr: # If this line produced a (possibly second) instruction
                 if len(binary_instr) != 32:
                     raise ValueError(f"Internal error: Generated instruction '{binary_instr}' is not 32 bits long!")
                 # Calculate the address for this specific instruction
                 current_instr_final_addr = instr_address + (4 * (instrs_generated - 1))
                 machine_code.append((current_instr_final_addr, binary_instr))
                 print(f"  Line {line_num}: 0x{current_instr_final_addr:08x} -> {binary_instr} ({opcode_mnem})")

            # Increment address based on how many instructions were generated
            if instrs_generated > 0:
                current_address += (4 * instrs_generated)
            # If 0 instructions (e.g., ignored directive), address doesn't change here


        except Exception as e:
            print(f"Error assembling line {line_num} ('{instruction_part}'): {e}", file=sys.stderr)
            error_occurred = True
            # Try to advance PC anyway to avoid cascading address errors
            # A better method would use line-number-to-address mapping from pass 1
            current_address += 4 # Crude estimate


    if error_occurred:
        print("\n--- Pass Two Completed with Errors ---", file=sys.stderr)
    else:
        print("--- Pass Two Complete ---")
    return machine_code

# --- Main Execution ---

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mips_assembler.py <input_asm_file> <output_bin_file> [output_hex_file]")
        sys.exit(1)

    input_filename = sys.argv[1]
    output_bin_filename = sys.argv[2]
    output_hex_filename = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        with open(input_filename, 'r') as infile:
            lines = infile.readlines()
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.", file=sys.stderr)
        sys.exit(1)

    # Run Pass One
    pass_one(lines)

    # Run Pass Two only if Pass One seemed okay (e.g., symbol table has entries or no errors reported)
    # Simple check: Did pass_one raise an exception? (More robust checks could be added)
    assembled_code = pass_two(lines)

    # Write Output Files only if assembly likely succeeded
    if assembled_code: # Check if list is not empty (implies pass two ran without fatal errors early on)
        try:
            with open(output_bin_filename, 'w') as binfile:
                # Sort by address just in case pseudo-ops caused out-of-order insertion
                assembled_code.sort(key=lambda item: item[0])
                for addr, code in assembled_code:
                    binfile.write(code + '\n')
            print(f"\nBinary machine code written to '{output_bin_filename}'")
        except IOError:
            print(f"Error: Could not write to binary output file '{output_bin_filename}'.", file=sys.stderr)
            sys.exit(1)

        if output_hex_filename:
            try:
                with open(output_hex_filename, 'w') as hexfile:
                    # Sort by address again for hex output
                    assembled_code.sort(key=lambda item: item[0])
                    for addr, code in assembled_code:
                        try:
                            hex_code = f"{int(code, 2):08x}" # Convert binary string to hex
                            hexfile.write(hex_code + '\n')
                        except ValueError:
                             print(f"Warning: Could not convert binary string '{code}' to hex. Skipping line.", file=sys.stderr)

                print(f"Hex machine code written to '{output_hex_filename}'")
            except IOError:
                print(f"Error: Could not write to hex output file '{output_hex_filename}'.", file=sys.stderr)

        print("\nAssembly complete.")
    else:
        print("\nAssembly failed or produced no code. Output files not written.", file=sys.stderr)
        sys.exit(1) # Exit with error status if assembly failed