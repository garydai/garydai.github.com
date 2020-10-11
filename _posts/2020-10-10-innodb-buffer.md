---
date: 2020-10-10
layout: default
title: innodb-buffer


---

# innodb-buffer

​	InnoDB中的数据访问是以Page为单位的，每个Page的大小默认为16KB，Buffer Pool是用来管理和缓存这些Page的。InnoDB将一块连续的内存大小划分给Buffer Pool来使用，并将其划分为多个Buffer Pool Instance来更好地管理这块内存，每个Instance的大小都是相等的，通过算法保证一个Page只会在一个特定的Instance中，划分为多个Instance的模式提升了Buffer Pool的并发性能。

​	每个Buffer Pool Instance中都有包含自己的锁，mutex，Buffer chunks，各个页链表（如下面所介绍），每个Instance之间都是独立的，支持多线程并发访问，且一个page只会被存放在一个固定的Instance中

/Users/daitechang/Documents/garydai.github.com/_posts/pic/261152517336796.png

mysql buffer pool里的三种链表和三种page

buffer pool是通过三种list来管理的
1) free list
2) lru list
3) flush list

**Buffer pool中的最小单位是page，在innodb中定义三种page**
1) free page :此page未被使用，此种类型page位于free链表中
2) clean page:此page被使用，对应数据文件中的一个页面，但是页面没有被修改，此种类型page位于lru链表中
3) dirty page:此page被使用，对应数据文件中的一个页面，但是页面被修改过，此种类型page位于lru链表和flush链表中

```c++
struct buf_pool_t { //保存Buffer Pool Instance级别的信息
    ...
    ulint instance_no; //当前buf_pool所属instance的编号
    ulint curr_pool_size; //当前buf_pool大小
    buf_chunk_t *chunks; //当前buf_pool中包含的chunks
    hash_table_t *page_hash; //快速检索已经缓存的Page
    UT_LIST_BASE_NODE_T(buf_page_t) free; //空闲Page链表
    UT_LIST_BASE_NODE_T(buf_page_t) LRU; //Page缓存链表，LRU策略淘汰
    UT_LIST_BASE_NODE_T(buf_page_t) flush_list; //还未Flush磁盘的脏页保存链表
    BufListMutex XXX_mutex; //各个链表的互斥Mutex
    ...
}
```

```c++
struct buf_block_t { //Page控制体
    buf_page_t page; //这个字段必须要放到第一个位置，这样才能使得buf_block_t和buf_page_t的指针进行						 转换
    byte *frame; //指向真正存储数据的Page
    BPageMutex mutex; //block级别的mutex
    ...
}
```

```c++
class buf_page_t {
	...
    page_id_t id; //page id
    page_size_t size; //page 大小
    ib_uint32_t buf_fix_count; //用于并发控制
    buf_io_fix io_fix; //用于并发控制
    buf_page_state state; //当前Page所处的状态，后续会详细介绍
    lsn_t newest_modification; //当前Page最新修改lsn
    lsn_t oldest_modification; //当前Page最老修改lsn，即第一条修改lsn
    ...
}
```

```c++
enum buf_page_state {
  BUF_BLOCK_POOL_WATCH, //看注释是给Purge使用的，先不关注
  BUF_BLOCK_ZIP_PAGE, //压缩Page状态，暂略过
  BUF_BLOCK_ZIP_DIRTY, //压缩页脏页状态，暂略过
  BUF_BLOCK_NOT_USED, //保存在Free List中的Page
  BUF_BLOCK_READY_FOR_USE, //当调用到buf_LRU_get_free_block获取空闲Page，此时被分配的Page就处于							这个状态
  BUF_BLOCK_FILE_PAGE, //正常被使用的状态，LRU List中的Page都是这个状态
  BUF_BLOCK_MEMORY, //用于存储非用户数据，比如系统数据的Page处于这个状态
  BUF_BLOCK_REMOVE_HASH //在Page从LRU List和Flush List中被回收并加入Free List时，需要先从							Page_hash中移除，此时Page处于这个状态
};
```



## 参考

http://mysql.taobao.org/monthly/2020/02/02/

https://www.cnblogs.com/jiangxu67/p/3765708.html