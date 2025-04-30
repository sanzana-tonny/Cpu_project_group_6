.text
main:
    li $t0, 0          # i = 0
    li $t1, 10         # count = 10
    li $t2, 0          # sum = 0
    li $t3, -2147483648 # max = lowest possible
    li $t4, 2147483647  # min = highest possible

    li $a0, 10
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 20
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 30
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 40
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 50
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 60
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 70
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 80
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 90
    jal update_sum
    jal update_max
    jal update_min

    li $a0, 100
    jal update_sum
    jal update_max
    jal update_min

    j compute

# Subroutine to update sum
update_sum:
    add $t2, $t2, $a0             # sum += input
    jr $ra

# Subroutine to update max
update_max:
    bgtz $a0, $t3, set_max
    jr $ra
set_max:
    move $t3, $a0                 # max = input
    jr $ra

# Subroutine to update min
update_min:
    bltz $a0, $t4, set_min
    jr $ra
set_min:
    move $t4, $a0                 # min = input
    jr $ra

compute:
    li $t5, 10
    div $t2, $t5
    mflo $t6                     # average = sum / 10

    # print max
    li $a0, 10                   # newline char
    li $v0, 11
    syscall

    li $v0, 1
    move $a0, $t3
    syscall                      # print max

    # print min
    li $a0, 10
    li $v0, 11
    syscall

    li $v0, 1
    move $a0, $t4
    syscall                      # print min

    # print avg
    li $a0, 10
    li $v0, 11
    syscall

    li $v0, 1
    move $a0, $t6
    syscall

    li $v0, 10
    syscall                      # exit
