---
date: 2020-3-29
layout: default
title: 分布式事务设计

---

# 分布式事务设计

![image-20200329213304820](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200329213304820.png)

怎么拦截spring管理的事务？

增加全局事务注解，优先级比spring事务要高。

先做全局事务逻辑，再执行spring事务逻辑

1. 增加事务注解

   创建全局事务，根据本地事务执行情况，发送全局事务指令

   ```java
   if (annotation.isStart()) {
     // 创建全局事务组，采用nettyclient发送创建事务组命令到事务协调器
     group = TransactionMangage.createGroup();
   } else {
     // 拿到当前事务组的ID
     group = TransactionMangage.getCurrent();
   }
   
   // 执行本地逻辑
   try {
       // Spring 会帮我们执行mysql的事务， 一直等待
       proceedingJoinPoint.proceed();
       //提交本地事物状态  ---commit
       TransactionMangage.commitTransaction(transaction, annotation.isEnd(), TransactionType.COMMIT);
   } catch (Throwable throwable) {
       // 回滚
       TransactionMangage.commitTransaction(transaction, annotation.isEnd(), TransactionType.ROLLBACK);
       throwable.printStackTrace();
   
   }
   ```

2. 改写connection

```
@Around("execution(* javax.sql.DataSource.getConnection(..))")
```

拦截获取connection的函数，commit的时候等待协调者发送提交指令

