.text
.globl main  # Good practice, might be required by your assembler

main:
    # li $t0, 0          # i = 0
    or $t0, $zero, $zero # More direct way to set to 0
    # li $t1, 10         # count = 10
    ori $t1, $zero, 10
    # li $t2, 0          # sum = 0
    or $t2, $zero, $zero
    # li $t3, -2147483648 # max = lowest possible (0x80000000)
    lui $t3, 0x8000      # Load upper immediate for min int
    # li $t4, 2147483647  # min = highest possible (0x7FFFFFFF)
    lui $t4, 0x7FFF      # Load upper immediate for max int
    ori $t4, $t4, 0xFFFF # Or immediate for lower part

    # Process 6
    ori $a0, $zero, 6
    jal update_sum
    jal update_max
    jal update_min

    # Process 8
    ori $a0, $zero, 8
    jal update_sum
    jal update_max
    jal update_min

    # Process 5
    ori $a0, $zero, 5
    jal update_sum
    jal update_max
    jal update_min

    # Process 17
    ori $a0, $zero, 17
    jal update_sum
    jal update_max
    jal update_min

    # Process 20
    ori $a0, $zero, 20
    jal update_sum
    jal update_max
    jal update_min

    # Process 12
    ori $a0, $zero, 12
    jal update_sum
    jal update_max
    jal update_min

    # Process 56
    ori $a0, $zero, 56
    jal update_sum
    jal update_max
    jal update_min

    # Process 32
    ori $a0, $zero, 32
    jal update_sum
    jal update_max
    jal update_min

    # Process 22
    ori $a0, $zero, 22
    jal update_sum
    jal update_max
    jal update_min

    # Process 3
    ori $a0, $zero, 3
    jal update_sum
    jal update_max
    jal update_min

    j compute

# Subroutine to update sum
update_sum:
    add $t2, $t2, $a0  # sum += input (add should be okay)
    jr $ra             # *** Still might fail if $ra isn't recognized ***

# Subroutine to update max
update_max:
    # bgt $a0, $t3, set_max -> becomes slt + bne
    slt $at, $t3, $a0      # Set $at=1 if $t3 < $a0 (i.e., $a0 > $t3)
    bne $at, $zero, set_max # Branch if $at is not zero (i.e., $a0 > $t3)
    jr $ra                 # *** Still might fail if $ra isn't recognized ***
set_max:
    # move $t3, $a0 -> becomes addu
    addu $t3, $zero, $a0   # max = input (using addu is common for move)
    jr $ra                 # *** Still might fail if $ra isn't recognized ***

# Subroutine to update min
update_min:
    # blt $a0, $t4, set_min -> becomes slt + bne
    slt $at, $a0, $t4      # Set $at=1 if $a0 < $t4
    bne $at, $zero, set_min # Branch if $at is not zero (i.e., $a0 < $t4)
    jr $ra                 # *** Still might fail if $ra isn't recognized ***
set_min:
    # move $t4, $a0 -> becomes addu
    addu $t4, $zero, $a0   # min = input
    jr $ra                 # *** Still might fail if $ra isn't recognized ***

compute:
    # li $t5, 10
    ori $t5, $zero, 10
    # div $t2, $t5
    div $t2, $t5           # Standard div instruction, result in HI/LO
    # mflo $t6             # average = sum / 10
    mflo $t6               # *** Still might fail if $t6 or mflo reg isn't recognized ***

    # Print results using syscalls

    # print newline (ASCII 10)
    ori $a0, $zero, 10     # Character to print
    ori $v0, $zero, 11     # Syscall code 11 for print character
    syscall

    # print max ($t3)
    ori $v0, $zero, 1      # Syscall code 1 for print integer
    addu $a0, $zero, $t3   # Move $t3 to $a0 for printing
    syscall

    # print newline
    ori $a0, $zero, 10
    ori $v0, $zero, 11
    syscall

    # print min ($t4)
    ori $v0, $zero, 1
    addu $a0, $zero, $t4
    syscall

    # print newline
    ori $a0, $zero, 10
    ori $v0, $zero, 11
    syscall

    # print avg ($t6)
    ori $v0, $zero, 1
    addu $a0, $zero, $t6 # *** Might fail if $t6 wasn't loaded correctly ***
    syscall

    # exit
    ori $v0, $zero, 10     # Syscall code 10 for exit
    syscall
