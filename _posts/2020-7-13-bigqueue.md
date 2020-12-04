---
date: 2020-7-13
layout: default
title: bigqueue

---

# bigqueue

https://github.com/bulldog2011/bigqueue

开源可持久化队列

![image-20200713151500698](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200713151500698.png)

![image-20200713152511421](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200713152511421.png)

## 入队列

插入数据步骤：根据header index找到相应的page文件，根据header偏移量插入数据

```java
public void enqueue(byte[] data) throws IOException {
    // bigQueue没开锁
    this.innerArray.append(data);

    this.completeFutures();
}
```

```java
public long append(byte[] data) throws IOException {
   try {
      // bigArray加读锁
      arrayReadLock.lock(); 
      IMappedPage toAppendDataPage = null;
      IMappedPage toAppendIndexPage = null;
      long toAppendIndexPageIndex = -1L;
      long toAppendDataPageIndex = -1L;
      
      long toAppendArrayIndex = -1L;
      
      try {
         appendLock.lock(); // only one thread can append
         
         // prepare the data pointer
         if (this.headDataItemOffset + data.length > DATA_PAGE_SIZE) { // not enough space
            this.headDataPageIndex++;
            this.headDataItemOffset = 0;
         }
         
         toAppendDataPageIndex = this.headDataPageIndex;
         int toAppendDataItemOffset  = this.headDataItemOffset;
         
         toAppendArrayIndex = this.arrayHeadIndex.get();
         
         // append data
         toAppendDataPage = this.dataPageFactory.acquirePage(toAppendDataPageIndex);
         ByteBuffer toAppendDataPageBuffer = toAppendDataPage.getLocal(toAppendDataItemOffset);
         toAppendDataPageBuffer.put(data);
         toAppendDataPage.setDirty(true);
         // update to next
         this.headDataItemOffset += data.length;
         
         toAppendIndexPageIndex = Calculator.div(toAppendArrayIndex, INDEX_ITEMS_PER_PAGE_BITS); // shift optimization
         toAppendIndexPage = this.indexPageFactory.acquirePage(toAppendIndexPageIndex);
         int toAppendIndexItemOffset = (int) (Calculator.mul(Calculator.mod(toAppendArrayIndex, INDEX_ITEMS_PER_PAGE_BITS), INDEX_ITEM_LENGTH_BITS));
         
         // update index
         ByteBuffer toAppendIndexPageBuffer = toAppendIndexPage.getLocal(toAppendIndexItemOffset);
         toAppendIndexPageBuffer.putLong(toAppendDataPageIndex);
         toAppendIndexPageBuffer.putInt(toAppendDataItemOffset);
         toAppendIndexPageBuffer.putInt(data.length);
         long currentTime = System.currentTimeMillis();
         toAppendIndexPageBuffer.putLong(currentTime);
         toAppendIndexPage.setDirty(true);
         
         // advance the head
         this.arrayHeadIndex.incrementAndGet();
         
         // update meta data
         IMappedPage metaDataPage = this.metaPageFactory.acquirePage(META_DATA_PAGE_INDEX);
         ByteBuffer metaDataBuf = metaDataPage.getLocal(0);
         metaDataBuf.putLong(this.arrayHeadIndex.get());
         metaDataBuf.putLong(this.arrayTailIndex.get());
         metaDataPage.setDirty(true);

      } finally {
         
         appendLock.unlock();
         
         if (toAppendDataPage != null) {
            this.dataPageFactory.releasePage(toAppendDataPageIndex);
         }
         if (toAppendIndexPage != null) {
            this.indexPageFactory.releasePage(toAppendIndexPageIndex);
         }
      }
      
      return toAppendArrayIndex;
   
   } finally {
      arrayReadLock.unlock();
   }
}
```





![image-20200713152343768](https://github.com/garydai/garydai.github.com/raw/master/_posts/pic/image-20200713152343768.png)

```java
    private static class ThreadLocalByteBuffer extends ThreadLocal<ByteBuffer> {
    	private ByteBuffer _src;
    	
    	public ThreadLocalByteBuffer(ByteBuffer src) {
    		_src = src;
    	}
    	
    	public ByteBuffer getSourceBuffer() {
    		return _src;
    	}
    	
    	@Override
    	protected synchronized ByteBuffer initialValue() {
        // 不能线程，底层缓存内容一样，pos、limit、cap等对象成员变量不一样
    		ByteBuffer dup = _src.duplicate();
    		return dup;
    	}
    }
```



```java
public IMappedPage acquirePage(long index) throws IOException {
   MappedPageImpl mpi = cache.get(index);
   if (mpi == null) { // not in cache, need to create one
      try {
         Object lock = null;
         synchronized(mapLock) {
            if (!pageCreationLockMap.containsKey(index)) {
               pageCreationLockMap.put(index, new Object());
            }
            lock = pageCreationLockMap.get(index);
         }
         synchronized(lock) { // only lock the creation of page index
            mpi = cache.get(index); // double check
            if (mpi == null) {
               RandomAccessFile raf = null;
               FileChannel channel = null;
               try {
                  String fileName = this.getFileNameByIndex(index);
                  raf = new RandomAccessFile(fileName, "rw");
                  channel = raf.getChannel();
                  MappedByteBuffer mbb = channel.map(READ_WRITE, 0, this.pageSize);
                  mpi = new MappedPageImpl(mbb, fileName, index);
                  cache.put(index, mpi, ttl);
                  if (logger.isDebugEnabled()) {
                     logger.debug("Mapped page for " + fileName + " was just created and cached.");
                  }
               } finally {
                  if (channel != null) channel.close();
                  if (raf != null) raf.close();
               }
            }
         }
      } finally {
         synchronized(mapLock) {
            pageCreationLockMap.remove(index);
         }
      }
    } else {
       if (logger.isDebugEnabled()) {
          logger.debug("Hit mapped page " + mpi.getPageFile() + " in cache.");
       }
    }

   return mpi;
}
```

## 出队列

加锁控制多线程访问

```java
 // locks for queue front write management
final Lock queueFrontWriteLock = new ReentrantLock();

public byte[] dequeue() throws IOException {
    long queueFrontIndex = -1L;
    try {
        // 加重入锁
        queueFrontWriteLock.lock();
        if (this.isEmpty()) {
            return null;
        }
        queueFrontIndex = this.queueFrontIndex.get();
        byte[] data = this.innerArray.get(queueFrontIndex);
        long nextQueueFrontIndex = queueFrontIndex;
        if (nextQueueFrontIndex == Long.MAX_VALUE) {
            nextQueueFrontIndex = 0L; // wrap
        } else {
            nextQueueFrontIndex++;
        }
        this.queueFrontIndex.set(nextQueueFrontIndex);
        // persist the queue front
        IMappedPage queueFrontIndexPage = this.queueFrontIndexPageFactory.acquirePage(QUEUE_FRONT_PAGE_INDEX);
        ByteBuffer queueFrontIndexBuffer = queueFrontIndexPage.getLocal(0);
        queueFrontIndexBuffer.putLong(nextQueueFrontIndex);
        queueFrontIndexPage.setDirty(true);
        return data;
    } finally {
        queueFrontWriteLock.unlock();
    }

}
```

```java
public byte[] get(long index) throws IOException {
   try {
      arrayReadLock.lock();
      validateIndex(index);
      
      IMappedPage dataPage = null;
      long dataPageIndex = -1L;
      try {
         // 取index数据
         ByteBuffer indexItemBuffer = this.getIndexItemBuffer(index);
         dataPageIndex = indexItemBuffer.getLong();
         int dataItemOffset = indexItemBuffer.getInt();
         int dataItemLength = indexItemBuffer.getInt();
         // 根据index，得到数据在文件里的page位置
         dataPage = this.dataPageFactory.acquirePage(dataPageIndex);
         byte[] data = dataPage.getLocal(dataItemOffset, dataItemLength);
         return data;
      } finally {
         if (dataPage != null) {
            this.dataPageFactory.releasePage(dataPageIndex);
         }
      }
   } finally {
      arrayReadLock.unlock();
   }
}
```

采用读写锁操作bigarray

采用可重入锁操作append数据

```java
// lock for appending state management
final Lock appendLock = new ReentrantLock();

// global lock for array read and write management
final ReadWriteLock arrayReadWritelock = new ReentrantReadWriteLock();
final Lock arrayReadLock = arrayReadWritelock.readLock();
final Lock arrayWriteLock = arrayReadWritelock.writeLock(); 
```