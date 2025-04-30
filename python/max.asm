.data
	array: .word 5 
	size: .word 5 
.text
.globl main
find_max:
    la $t0, array 
    lw $t1, size
    lw $t2, 0($t0)
    move $t4, $t2
    li $t6, 0
	loop_max:
    beq $t6, $t1, end_max
lw $t7, 0($t0)
bgt $t7, $t4, update_max
    j skip_max
update_max:
    move $t4, $t7	
skip_max:
    addi $t6, $t6, 1
    addi $t0, $t0, 4
    j loop_max
end_max:
    move $a0, $t4
	li $v0, 10
    syscall