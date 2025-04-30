    .text
main:
    li $a0, 5
    li $a1, 7
    jal add_numbers
    sw $v0, 100($0)

add_numbers:
    add $v0, $a0, $a1
    jr $ra
