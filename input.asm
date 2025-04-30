.data
prompt: .asciiz "Enter a number: "
result: .asciiz "The result is: "
newline:.asciiz "\n"
value:  .word 0
.text
main:
    la $a0, prompt
    li $v0, 4
    syscall
    li $v0, 5
    syscall
    move $t0, $v0
    sw $t0, 0(value)
    li $t2, 2
    mult $t0, $t2
    mflo $t1

    la $a0, result
    li $v0, 4
    syscall

    li $v0, 1
    move $a0, $t1
    syscall
    la $a0, newline
    li $v0, 4
    syscall
j exit
add $t5, $t5, $t5
exit:
   
    li $v0, 10
    syscall
