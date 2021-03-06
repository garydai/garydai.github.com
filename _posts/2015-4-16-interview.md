---
date: 2015-4-16
layout: default
title: 面试题

---

##面试题

1.题目：输入一棵二元查找树，将该二元查找树转换成一个排序的双向链表。要求不能创建任何新的结点，只调整指针的指向。



2.题目：求1+2+…+n，要求不能使用乘除法、for、while、if、else、switch、case等关键字以及条件判断语句（A?B:C）。

3.题目：输入一个单向链表，输出该链表中倒数第k个结点。链表的倒数第0个结点为链表的尾指针。

4.题目：输入一个已经按升序排序过的数组和一个数字，在数组中查找两个数，使得它们的和正好是输入的那个数字。要求时间复杂度是O(n)。如果有多对数字的和等于输入的数字，输出任意一对即可。

例如输入数组1、2、4、7、11、15和数字15。由于4+11=15，因此输出4和11。

5.题目：在一个字符串中找到第一个只出现一次的字符。如输入abaccdeff，则输出b。

6.题目：n个数字（0,1,…,n-1）形成一个圆圈，从数字0开始，每次从这个圆圈中删除第m个数字（第一个为当前数字本身，第二个为当前数字的下一个数字）。当一个数字删除后，从被删除数字的下一个继续删除第m个数字。求出在这个圆圈中剩下的最后一个数字。

7.题目：定义Fibonacci数列如下：

		        /  0                      n=0
		f(n)=      1                      n=1
		        \  f(n-1)+f(n-2)          n=2

输入n，用最快的方法求该数列的第n项。


8.题目：输入一个字符串，打印出该字符串中字符的所有排列。例如输入字符串abc，则输出由字符a、b、c所能排列出来的所有字符串abc、acb、bac、bca、cab和cba。

扩展1：如果不是求字符的所有排列，而是求字符的所有组合，应该怎么办呢？当输入的字符串中含有相同的字符串时，相同的字符交换位置是不同的排列，但是同一个组合。举个例子，如果输入abc，它的组合有a、b、c、ab、ac、bc、abc。

扩展2：输入一个含有8个数字的数组，判断有没有可能把这8个数字分别放到正方体的8个顶点上，使得正方体上三组相对的面上的4个顶点的和相等。


9.题目：输入一棵二元树的根结点，求该树的深度。从根结点到叶结点依次经过的结点（含根、叶结点）形成树的一条路径，最长路径的长度为树的深度。

10.题目：输入一个正数n，输出所有和为n连续正数序列。(O(logn))

例如输入15，由于1+2+3+4+5=4+5+6=7+8=15，所以输出3个连续序列1-5、4-6和7-8。

11.题目：输入一个整数n，求从1到n这n个整数的十进制表示中1出现的次数。

例如输入12，从1到12这些整数中包含1 的数字有1，10，11和12，1一共出现了5次。

12.题目：输入一个正整数数组，将它们连接起来排成一个数，输出能排出的所有数字中最小的一个。例如输入数组{32,  321}，则输出这两个能排成的最小数字32132。请给出解决问题的算法，并证明该算法。


13.题目：输入两个字符串，从第一字符串中删除第二个字符串中所有的字符。例如，输入”They are students.”和”aeiou”，则删除之后的第一个字符串变成”Thy r stdnts.”。

14.题目：输入一个字符串，输出该字符串中对称的子字符串的最大长度。比如输入字符串“google”，由于该字符串里最长的对称子字符串是“goog”，因此输出4。

15.题目：数组中有一个数字出现的次数超过了数组长度的一半，找出这个数字。

16.题目：二叉树的结点定义如下：

	struct TreeNode
	{
	    int m_nvalue;
	    TreeNode* m_pLeft;
	    TreeNode* m_pRight;
	};
输入二叉树中的两个结点，输出这两个结点在数中最低的共同父结点。


---------------------------------------------------------------------


1.1 中序遍历，保存节点，遍历节点改变指针指向

1.2 边遍历边调整指针指向

2.1.构造函数

2.2.递归，0的时候如何返回是难点

3.双指针

4.数组两边向中间靠拢

5.哈希

6.递归

7.有个logn的算法

8.全排列，利于对递归的理解

9.递归

10.

11.计算各个位置为1的个数

12.因为ab<ba所以a排在b前面 a<b, 证明a<b b<c => a<c

13.删除有技巧

14.O(n2)

15.O(n)

16.1 递归

16.2 两个链表的交叉点




