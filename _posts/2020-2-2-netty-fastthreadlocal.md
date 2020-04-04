---
date: 2020-2-2
layout: default
title: netty-FastThreadLocal

---

# netty-FastThreadLocal

索引：将threadlocal存到线程thread对象的数组成员变量，索引值是递增整形，而jdk的threadlocal用的是hash，再使用线性检测解决冲突

![image-20200204113937596](/Users/daitechang/Documents/hexo_blog/source/_posts/pic/image-20200204113937596.png)