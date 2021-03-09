---
date: 2021-3-9
layout: default
title: SynchronousQueue




---

# SynchronousQueue

SynchronousQueue是一个双栈双队列算法，无空间的队列或栈，任何一个对SynchronousQueue写需要等到一个对SynchronousQueue的读操作，反之亦然。一个读操作需要等待一个写操作，相当于是交换通道，提供者和消费者是需要组队完成工作，缺少一个将会阻塞线程，知道等到配对为止。

SynchronousQueue是一个队列和栈算法实现，在SynchronousQueue中双队列FIFO提供公平模式，而双栈LIFO提供的则是非公平模式。



## 参考

https://segmentfault.com/a/1190000019153021