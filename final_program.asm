.text
main:
    li $t1, 0x10010000
    li $t0, 25
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, -5
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, 100
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, 0
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, 50
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, -20
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, 75
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, 10
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, 99
    sw $t0, 0($t1)
    addi $t1, $t1, 4
    li $t0, 33
    sw $t0, 0($t1)
    li $a0, 0x10010000
    li $a1, 10
    jal find_max
    sll $zero, $zero, 0
    li $t0, 0x10010080
    sw $v0, 0($t0)
    li $a0, 0x10010000
    li $a1, 10
    jal find_min
    sll $zero, $zero, 0
    li $t0, 0x10010084
    sw $v0, 0($t0)
    li $a0, 0x10010000
    li $a1, 10
    jal find_mean
    sll $zero, $zero, 0
    li $t0, 0x10010088
    sw $v0, 0($t0)
    li $v0, 10
    syscall
find_max:
    move $t0, $a0
    move $t1, $a1
    lw $t4, 0($t0)
    li $t6, 1
    addi $t0, $t0, 4
loop_max:
    beq $t6, $t1, end_max
    sll $zero, $zero, 0
    lw $t7, 0($t0)
    slt $at, $t4, $t7
    bne $at, $zero, update_max
    sll $zero, $zero, 0
    j skip_max
    sll $zero, $zero, 0
update_max:
    move $t4, $t7
skip_max:
    addi $t6, $t6, 1
    addi $t0, $t0, 4
    j loop_max
    sll $zero, $zero, 0
end_max:
    move $v0, $t4
    jr $ra
    sll $zero, $zero, 0
find_min:
    move $t0, $a0
    move $t1, $a1
    lw $t3, 0($t0)
    li $t6, 1
    addi $t0, $t0, 4
loop_min:
    beq $t6, $t1, end_min
    sll $zero, $zero, 0
    lw $t7, 0($t0)
    slt $at, $t7, $t3
    bne $at, $zero, update_min
    sll $zero, $zero, 0
    j skip_min
    sll $zero, $zero, 0
update_min:
    move $t3, $t7
skip_min:
    addi $t6, $t6, 1
    addi $t0, $t0, 4
    j loop_min
    sll $zero, $zero, 0
end_min:
    move $v0, $t3
    jr $ra
    sll $zero, $zero, 0
find_mean:
    addi $sp, $sp, -4
    sw $ra, 0($sp)
    move $t0, $a0
    move $t1, $a1
    move $t5, $zero
    li $t6, 0
loop_mean:
    beq $t6, $t1, end_mean_loop
    sll $zero, $zero, 0
    lw $t7, 0($t0)
    add $t5, $t5, $t7
    addi $t6, $t6, 1
    addi $t0, $t0, 4
    j loop_mean
    sll $zero, $zero, 0
end_mean_loop:
    move $a0, $t5
    move $a1, $t1
    jal divide
    sll $zero, $zero, 0
    lw $ra, 0($sp)
    addi $sp, $sp, 4
    jr $ra
    sll $zero, $zero, 0
divide:
    move $t0, $a0
    move $t1, $a1
    li $t2, 0
    blez $t1, end_division
    sll $zero, $zero, 0
dloop:
    slt $at, $t0, $t1
    bne $at, $zero, end_division
    sll $zero, $zero, 0
    sub $t0, $t0, $t1
    addi $t2, $t2, 1
    j dloop
    sll $zero, $zero, 0
end_division:
    move $v0, $t2
    jr $ra
    sll $zero, $zero, 0