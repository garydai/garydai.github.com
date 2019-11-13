---
layout: default

title: thread_local

---

# ThreadLocal

```
Thread.ThreadLocalMap;
```

1. Thread: 当前线程，可以通过Thread.currentThread()获取。
2. ThreadLocal：我们的static ThreadLocal变量。
3. Object: 当前线程共享变量。

我们调用ThreadLocal.get方法时，实际上是从当前线程中获取ThreadLocalMap<ThreadLocal, Object>，然后根据当前ThreadLocal获取当前线程共享变量Object。