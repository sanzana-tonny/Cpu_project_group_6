.data 
	 array: .word 5 
	 size: .word 5 
.text
.globl main
main:
    la $t0, array 
    lw $t1, size
lw $t2, 0($t0)
    move $t3, $t2
    li $t6, 0
loop_min:
    beq $t6, $t1, end_min
    lw $t7, 0($t0)
    blt $t7, $t3, update_min
    j skip_min
update_min:
    move $t3, $t7
skip_min:
    addi $t6, $t6, 1
    addi $t0, $t0, 4
    j loop_min
end_min:
    move $a0, $t3
	li $v0, 10
    syscall