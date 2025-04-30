.data 
	 array: .word 5 
	 size: .word 5
.text
.globl main
main:
    la $t0, array 
    lw $t1, size
move $t5, $zero
li $t6, 0	
loop_mean:
    beq $t6, $t1, end_mean
lw $t7, 0($t0)
add $t5, $t5, $t7
addi $t6, $t6, 1
    addi $t0, $t0, 4
	j loop_mean
end_mean:
    div $t5, $t1
	mflo $a0
li $v0, 10
    syscall