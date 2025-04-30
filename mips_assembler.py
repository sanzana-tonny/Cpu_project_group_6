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
            n = int(n, 0) # Automatically detect base (e.g., 0x for hex)
        except ValueError:
            raise ValueError(f"Invalid immediate value: {n}")

    if n >= 0:
        # Positive number or zero
        s = bin(n)[2:] # Remove '0b' prefix
        if len(s) > bits:
            raise ValueError(f"Value {n} too large for {bits} bits")
        return s.zfill(bits) # Pad with leading zeros
    else:
        # Negative number (two's complement)
        # Calculate 2's complement for 'bits' length
        # Check if the negative number is representable
        if n < -(2**(bits-1)):
             raise ValueError(f"Value {n} too small for {bits} bits (signed)")
        # Compute the positive equivalent in 2's complement
        val = (1 << bits) + n
        s = bin(val)[2:]
        if len(s) > bits: # Should not happen if range check is correct, but safety
             return s[-bits:] # Take lower bits if overflow somehow occured
        return s.zfill(bits)


def parse_operands(ops_str):
    """Parses comma-separated operands, handling imm(reg) format."""
    ops = []
    # Regex to handle 'imm(reg)' format correctly without splitting imm
    # It splits by comma, unless the comma is inside parentheses
    for part in re.split(r",\s*(?![^()]*\))", ops_str):
        ops.append(part.strip())
    return ops

def parse_mem_operand(op):
    """Parses 'imm(reg)' or 'label(reg)' format, returns (imm/label, reg)."""
    match = re.match(r"([\w\d.-]+)\s*\(\s*(\$\w+)\s*\)", op) # Allow hex/decimal immediate
    if match:
        return match.group(1), match.group(2)
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
    global current_address, in_text_section, base_address_text
    pc = base_address_text # Program counter simulation for text segment
    data_pc = base_address_data # Address counter for data segment

    print("--- Pass One: Building Symbol Table ---")
    for line_num, line in enumerate(lines, 1):
        cleaned = clean_line(line)
        if not cleaned:
            continue # Skip empty lines and comments

        # Check for section directives first
        if cleaned == ".data":
            in_text_section = False
            print(f"  Line {line_num}: Switched to .data section")
            continue
        elif cleaned == ".text":
            in_text_section = True
            current_address = pc # Track address in text segment
            print(f"  Line {line_num}: Switched to .text section")
            continue

        # Check for labels
        match = re.match(r"^\s*(\w+):\s*(.*)", cleaned)
        label = None
        instruction_part = cleaned
        if match:
            label = match.group(1)
            instruction_part = match.group(2).strip()
            if not instruction_part and not in_text_section:
                 # Label definition without data directive on same line (e.g., label:\n .word 0)
                 # Store the address, but don't advance data_pc yet.
                 if label in symbol_table or label in data_symbol_table:
                     print(f"Error line {line_num}: Label '{label}' already defined.", file=sys.stderr)
                     # Decide how to handle error, maybe exit later
                 if in_text_section:
                     symbol_table[label] = pc
                     print(f"  Line {line_num}: Found text label '{label}' at address 0x{pc:08x}")
                 else:
                     data_symbol_table[label] = data_pc
                     print(f"  Line {line_num}: Found data label '{label}' at address 0x{data_pc:08x}")
                 continue # Don't process rest of line if only label def
            elif label:
                 # Label definition on same line as instruction/directive
                 if label in symbol_table or label in data_symbol_table:
                     print(f"Error line {line_num}: Label '{label}' already defined.", file=sys.stderr)
                 if in_text_section:
                     symbol_table[label] = pc
                     print(f"  Line {line_num}: Found text label '{label}' at address 0x{pc:08x}")
                 else:
                     data_symbol_table[label] = data_pc
                     print(f"  Line {line_num}: Found data label '{label}' at address 0x{data_pc:08x}")


        if not instruction_part:
             continue # Skip lines with only labels

        # Process based on section
        if in_text_section:
            # Simulate PC increment for instructions in text section
            parts = instruction_part.split(None, 1)
            opcode = parts[0].lower()
            # Handle pseudo-instructions that expand to multiple instructions
            if opcode == "li":
                pc += 8 # lui + ori
            elif opcode == "la":
                 pc += 8 # lui + ori
            elif opcode == "move":
                 pc += 4 # Usually one 'addu'
            elif opcode in r_type_instructions or \
                 opcode in i_type_instructions or \
                 opcode in j_type_instructions:
                pc += 4 # Most instructions take 4 bytes
            else:
                 # Could be a directive within .text, ignore for PC calc or handle if needed
                 # Or could be an error (unknown instruction) - will be caught in pass two
                 pass
            current_address = pc # Keep track for potential relative branches
        else:
            # Handle data directives in data section to advance data_pc
            parts = instruction_part.split(None, 1)
            directive = parts[0].lower()
            args_str = parts[1] if len(parts) > 1 else ""
            if directive == ".word":
                num_words = len(args_str.split(','))
                data_pc += 4 * num_words
                print(f"  Line {line_num}: Found .word directive, size {4 * num_words}, next data addr 0x{data_pc:08x}")
            elif directive == ".space":
                try:
                    size = int(args_str.strip())
                    data_pc += size
                    print(f"  Line {line_num}: Found .space directive, size {size}, next data addr 0x{data_pc:08x}")
                except ValueError:
                     print(f"Error line {line_num}: Invalid size for .space: {args_str}", file=sys.stderr)
            elif directive == ".asciiz":
                match_str = re.search(r'"(.*)"', args_str)
                if match_str:
                    size = len(match_str.group(1).encode('ascii').decode('unicode_escape')) + 1 # +1 for null terminator
                    data_pc += size
                    print(f"  Line {line_num}: Found .asciiz directive, size {size}, next data addr 0x{data_pc:08x}")
                else:
                     print(f"Error line {line_num}: Invalid string for .asciiz: {args_str}", file=sys.stderr)
            elif directive == ".ascii":
                 match_str = re.search(r'"(.*)"', args_str)
                 if match_str:
                     size = len(match_str.group(1).encode('ascii').decode('unicode_escape'))
                     data_pc += size
                     print(f"  Line {line_num}: Found .ascii directive, size {size}, next data addr 0x{data_pc:08x}")
                 else:
                     print(f"Error line {line_num}: Invalid string for .ascii: {args_str}", file=sys.stderr)
            elif directive == ".byte":
                 num_bytes = len(args_str.split(','))
                 data_pc += num_bytes
                 print(f"  Line {line_num}: Found .byte directive, size {num_bytes}, next data addr 0x{data_pc:08x}")
            elif directive == ".align":
                 # Simple alignment for now
                 try:
                     align_val = int(args_str.strip())
                     align_bytes = 2**align_val
                     offset = (align_bytes - (data_pc % align_bytes)) % align_bytes
                     data_pc += offset
                     print(f"  Line {line_num}: Found .align directive {align_val}, adding {offset} bytes, next data addr 0x{data_pc:08x}")
                 except ValueError:
                      print(f"Error line {line_num}: Invalid value for .align: {args_str}", file=sys.stderr)


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

    print("\n--- Pass Two: Generating Machine Code ---")
    for line_num, line in enumerate(lines, 1):
        cleaned = clean_line(line)
        if not cleaned:
            continue

        if cleaned == ".data":
            in_text_section = False
            continue
        elif cleaned == ".text":
            in_text_section = True
            # current_address should already be correct from Pass 1 simulation if only labels follow
            # Re-sync if necessary, though usually handled by tracking instructions
            continue

        if not in_text_section:
            continue # Only assemble .text section

        # Strip label definitions for instruction parsing
        instruction_part = re.sub(r"^\s*\w+:\s*", "", cleaned).strip()
        if not instruction_part:
            continue # Skip lines with only labels

        parts = instruction_part.split(None, 1)
        opcode_mnem = parts[0].lower()
        ops_str = parts[1] if len(parts) > 1 else ""
        operands = parse_operands(ops_str)

        binary_instr = None
        instr_address = current_address # Address of the *current* instruction being assembled

        try:
            # R-Type
            if opcode_mnem in r_type_instructions:
                funct = r_type_instructions[opcode_mnem]
                rs, rt, rd, shamt = "00000", "00000", "00000", "00000"
                opcode = "000000"

                if opcode_mnem in ["add", "addu", "sub", "subu", "and", "or", "xor", "nor", "slt", "sltu"]:
                    # Format: op $rd, $rs, $rt
                    if len(operands) != 3: raise ValueError("Expected 3 operands (rd, rs, rt)")
                    rd = registers[operands[0]]
                    rs = registers[operands[1]]
                    rt = registers[operands[2]]
                elif opcode_mnem in ["sll", "srl", "sra"]:
                    # Format: op $rd, $rt, shamt
                    if len(operands) != 3: raise ValueError("Expected 3 operands (rd, rt, shamt)")
                    rd = registers[operands[0]]
                    rt = registers[operands[1]]
                    shamt = decimal_to_binary(int(operands[2]), 5)
                    rs = "00000" # rs is not used
                elif opcode_mnem == "jr":
                    # Format: jr $rs
                    if len(operands) != 1: raise ValueError("Expected 1 operand (rs)")
                    rs = registers[operands[0]]
                    rt, rd, shamt = "00000", "00000", "00000"
                elif opcode_mnem == "jalr":
                     # Format: jalr $rs OR jalr $rd, $rs
                     if len(operands) == 1:
                         rs = registers[operands[0]]
                         rd = registers["$ra"] # Default $rd is $ra (31)
                         rt = "00000"
                     elif len(operands) == 2:
                         rd = registers[operands[0]]
                         rs = registers[operands[1]]
                         rt = "00000"
                     else: raise ValueError("Expected 1 or 2 operands (rs) or (rd, rs)")
                elif opcode_mnem in ["mult", "multu", "div", "divu"]:
                    # Format: op $rs, $rt
                    if len(operands) != 2: raise ValueError("Expected 2 operands (rs, rt)")
                    rs = registers[operands[0]]
                    rt = registers[operands[1]]
                    rd, shamt = "00000", "00000"
                elif opcode_mnem in ["mfhi", "mflo"]:
                     # Format: op $rd
                     if len(operands) != 1: raise ValueError("Expected 1 operand (rd)")
                     rd = registers[operands[0]]
                     rs, rt, shamt = "00000", "00000", "00000"
                elif opcode_mnem == "syscall":
                     if len(operands) != 0: raise ValueError("Expected 0 operands")
                     # Specific format for syscall
                     funct = "001100"
                     rs = rt = rd = shamt = "00000"
                     opcode = "000000" # Correct opcode
                     binary_instr = f"{opcode}{rs}{rt}{rd}{shamt}{funct}" # Special case format

                if binary_instr is None: # Avoid overwriting syscall
                    binary_instr = f"{opcode}{rs}{rt}{rd}{shamt}{funct}"

            # I-Type
            elif opcode_mnem in i_type_instructions:
                opcode = i_type_instructions[opcode_mnem]
                rs, rt, imm = "00000", "00000", "0000000000000000"

                if opcode_mnem in ["addi", "addiu", "andi", "ori", "xori", "slti", "sltiu"]:
                    # Format: op $rt, $rs, immediate
                    if len(operands) != 3: raise ValueError("Expected 3 operands (rt, rs, imm)")
                    rt = registers[operands[0]]
                    rs = registers[operands[1]]
                    imm = decimal_to_binary(operands[2], 16)
                elif opcode_mnem == "lui":
                    # Format: lui $rt, immediate
                    if len(operands) != 2: raise ValueError("Expected 2 operands (rt, imm)")
                    rt = registers[operands[0]]
                    imm = decimal_to_binary(operands[1], 16)
                    rs = "00000" # rs is not used
                elif opcode_mnem in ["lw", "sw", "lb", "lbu", "lh", "lhu", "sb", "sh"]:
                    # Format: op $rt, offset($rs) or op $rt, label($rs)
                    if len(operands) != 2: raise ValueError("Expected 2 operands (rt, offset(rs))")
                    rt = registers[operands[0]]
                    offset_or_label, rs_reg = parse_mem_operand(operands[1])
                    rs = registers[rs_reg]
                    # Check if offset_or_label is a data label
                    if offset_or_label in data_symbol_table:
                         # This assumes simple offset 0 from data label - LA handles full address
                         # A more complex assembler might handle label + offset here
                         # For basic lw/sw with labels, often use LA first then 0($reg)
                         # If we allow 'lw $t0, mydata($zero)', need data address here.
                         # Simplified: assume numeric offset or handle label error
                         raise ValueError(f"Direct use of data label '{offset_or_label}' in lw/sw offset not supported (use 'la' first)")
                    else:
                         imm = decimal_to_binary(offset_or_label, 16) # Numeric offset
                elif opcode_mnem in ["beq", "bne"]:
                    # Format: op $rs, $rt, label
                    if len(operands) != 3: raise ValueError("Expected 3 operands (rs, rt, label)")
                    rs = registers[operands[0]]
                    rt = registers[operands[1]]
                    label = operands[2]
                    if label not in symbol_table: raise ValueError(f"Label '{label}' not found")
                    target_addr = symbol_table[label]
                    # PC-relative addressing: offset = (target_addr - (current_instr_addr + 4)) / 4
                    offset = (target_addr - (instr_address + 4)) >> 2 # Use '>> 2' for / 4
                    imm = decimal_to_binary(offset, 16)

                binary_instr = f"{opcode}{rs}{rt}{imm}"

            # J-Type
            elif opcode_mnem in j_type_instructions:
                opcode = j_type_instructions[opcode_mnem]
                # Format: op label
                if len(operands) != 1: raise ValueError("Expected 1 operand (label)")
                label = operands[0]
                if label not in symbol_table: raise ValueError(f"Label '{label}' not found")
                target_addr = symbol_table[label]
                # MIPS address is upper 4 bits of PC | (target_addr / 4) | 00
                # We need the lower 26 bits of the target address, shifted right by 2 (divided by 4)
                jump_target = (target_addr & 0x0FFFFFFF) >> 2 # Mask to be safe, shift
                address = decimal_to_binary(jump_target, 26)
                binary_instr = f"{opcode}{address}"

            # --- Pseudo-Instructions ---
            elif opcode_mnem == "move":
                 # move $rt, $rs -> addu $rt, $rs, $zero
                 if len(operands) != 2: raise ValueError("Expected 2 operands (rt, rs)")
                 rt = registers[operands[0]]
                 rs = registers[operands[1]]
                 rd = rt
                 funct = r_type_instructions["addu"]
                 shamt = "00000"
                 binary_instr = f"000000{rs}{registers['$zero']}{rd}{shamt}{funct}"

            elif opcode_mnem == "li":
                # li $rt, immediate
                if len(operands) != 2: raise ValueError("Expected 2 operands (rt, immediate)")
                rt = registers[operands[0]]
                try:
                    imm_val = int(operands[1], 0) # Handle dec/hex immediate
                except ValueError: raise ValueError(f"Invalid immediate value for li: {operands[1]}")

                # If immediate fits in 16 bits (and is positive for ori), use single ori
                # If it's negative or > 16 bits (signed), might need lui+ori
                # Simplification: Always use lui + ori for 32-bit values
                # Check if it fits in 16 bits unsigned for optimization (ori $rt, $zero, imm)
                if 0 <= imm_val <= 0xFFFF:
                     # Use: ori $rt, $zero, imm
                     opcode = i_type_instructions["ori"]
                     rs = registers["$zero"]
                     imm_bin = decimal_to_binary(imm_val, 16)
                     binary_instr = f"{opcode}{rs}{rt}{imm_bin}"
                else:
                     # Use: lui $at, upper_16_bits
                     #      ori $rt, $at, lower_16_bits
                     upper = (imm_val >> 16) & 0xFFFF
                     lower = imm_val & 0xFFFF

                     # LUI instruction
                     opcode_lui = i_type_instructions["lui"]
                     rs_lui = "00000"
                     rt_lui = registers["$at"] # Use $at register
                     imm_lui = decimal_to_binary(upper, 16)
                     instr1 = f"{opcode_lui}{rs_lui}{rt_lui}{imm_lui}"
                     machine_code.append((instr_address, instr1)) # Add first instruction
                     print(f"  Line {line_num} (li expansion): 0x{instr_address:08x} -> {instr1} (lui)")
                     current_address += 4 # Increment PC for the LUI part

                     # ORI instruction
                     opcode_ori = i_type_instructions["ori"]
                     rs_ori = registers["$at"] # Use $at from LUI
                     # rt is the original target register
                     imm_ori = decimal_to_binary(lower, 16)
                     binary_instr = f"{opcode_ori}{rs_ori}{rt}{imm_ori}"
                     # The main loop will add this second instruction

            elif opcode_mnem == "la":
                # la $rt, label
                if len(operands) != 2: raise ValueError("Expected 2 operands (rt, label)")
                rt = registers[operands[0]]
                label = operands[1]
                if label not in symbol_table: raise ValueError(f"Label '{label}' not found")

                addr = symbol_table[label]
                upper = (addr >> 16) & 0xFFFF
                lower = addr & 0xFFFF

                # LUI $at, upper_16_bits
                opcode_lui = i_type_instructions["lui"]
                rs_lui = "00000"
                rt_lui = registers["$at"]
                imm_lui = decimal_to_binary(upper, 16)
                instr1 = f"{opcode_lui}{rs_lui}{rt_lui}{imm_lui}"
                machine_code.append((instr_address, instr1))
                print(f"  Line {line_num} (la expansion): 0x{instr_address:08x} -> {instr1} (lui)")
                current_address += 4

                # ORI $rt, $at, lower_16_bits (only needed if lower bits are non-zero)
                if lower != 0:
                     opcode_ori = i_type_instructions["ori"]
                     rs_ori = registers["$at"]
                     imm_ori = decimal_to_binary(lower, 16)
                     binary_instr = f"{opcode_ori}{rs_ori}{rt}{imm_ori}"
                else:
                     # If lower is 0, the LUI result in $at is the final address
                     # We need to move it to the target register $rt
                     # Use: addu $rt, $at, $zero
                     funct = r_type_instructions["addu"]
                     shamt = "00000"
                     binary_instr = f"000000{registers['$at']}{registers['$zero']}{rt}{shamt}{funct}"


            # Add more pseudo-instructions here (blt, bgt, etc.) if needed

            else:
                raise ValueError(f"Unknown instruction mnemonic: '{opcode_mnem}'")

            # If binary_instr was generated (and not handled by multi-instr pseudo-op)
            if binary_instr:
                 if len(binary_instr) != 32:
                     raise ValueError(f"Internal error: Generated instruction '{binary_instr}' is not 32 bits long!")
                 machine_code.append((instr_address, binary_instr))
                 print(f"  Line {line_num}: 0x{instr_address:08x} -> {binary_instr} ({opcode_mnem})")

            # Increment PC for the next instruction (handle multi-instruction pseudo-ops correctly)
            # The increment logic is now primarily handled within the pseudo-instruction expansion
            # Single instructions or the last part of a pseudo-instruction increment here.
            if opcode_mnem not in ["li", "la"]: # These handle their own increments
                 current_address += 4
            elif opcode_mnem == "li" and (0 <= imm_val <= 0xFFFF): # Single ORI for li
                 current_address += 4
            # 'la' always takes 2 instructions (or move), handled above

        except Exception as e:
            print(f"Error assembling line {line_num} ('{instruction_part}'): {e}", file=sys.stderr)
            # Optionally: sys.exit(1) or collect errors and report at the end

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

    # Run Pass Two
    assembled_code = pass_two(lines)

    # Write Output Files
    try:
        with open(output_bin_filename, 'w') as binfile:
            for addr, code in assembled_code:
                binfile.write(code + '\n')
        print(f"\nBinary machine code written to '{output_bin_filename}'")
    except IOError:
        print(f"Error: Could not write to binary output file '{output_bin_filename}'.", file=sys.stderr)
        sys.exit(1)

    if output_hex_filename:
        try:
            with open(output_hex_filename, 'w') as hexfile:
                for addr, code in assembled_code:
                    hex_code = f"{int(code, 2):08x}" # Convert binary string to hex
                    hexfile.write(hex_code + '\n')
            print(f"Hex machine code written to '{output_hex_filename}'")
        except IOError:
            print(f"Error: Could not write to hex output file '{output_hex_filename}'.", file=sys.stderr)
        except ValueError:
             print(f"Error: Could not convert binary code to hex.", file=sys.stderr)


    print("\nAssembly complete.")