---
date: 2020-1-20
layout: default
title: docker
---

# docker

## Cgroup

资源控制

![image-20200412203739705](/Users/daitechang/Documents/garydai.github.com/_posts/pic/image-20200412203739705.png)

cgroup 是一种特殊的文件系统

```c

struct file_system_type cgroup_fs_type = {
  .name = "cgroup",
  .mount = cgroup_mount,
  .kill_sb = cgroup_kill_sb,
  .fs_flags = FS_USERNS_MOUNT,
};
```



## namespace

访问隔离

### Network Namespace

![image-20200502110410734](/Users/daitechang/Documents/garydai.github.com/_posts/pic/image-20200502110410734.png)

## rootfs

文件系统隔离。镜像的本质就是一个rootfs文件

## 容器引擎

生命周期控制



## 参考

https://coolshell.cn/articles/17010.html

https://time.geekbang.org/column/article/115582