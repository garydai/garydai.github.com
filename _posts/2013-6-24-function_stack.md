---
date: 2013-6-24
layout: default
title: 函数与栈

---
##函数与栈
###调用函数过程
压栈函数参数，压入返回地址(调用函数的下一条指令地址),压入老的栈底，压入调用方的寄存器和临时空间(可选)。   
###函数返回值
1.函数的返回值，通过寄存器eax传递给调用方，函数把返回值赋给eax。返回值大小最多64位，两个寄存器。     

2.若大于64位的返回值(一个结构或类)，首先在栈上分配一块空间，然后把空间地址赋给eax，再把eax寄存器压入栈，相当于传入一个隐藏的函数参数，把返回值复制到eax指向的空间里。所以返回值保存在eax指向的空间里。 







