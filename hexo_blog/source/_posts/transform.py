# -*- coding: UTF-8 -*-
import os
import re
path = "." #文件夹目录
files= os.listdir(path) #得到文件夹下的所有文件名称
s = []
for file in files: #遍历文件夹
    if not os.path.isdir(file): #判断是否是文件夹，不是文件夹才打开
    	#print file
    	m = re.match('^[0-9]*-[0-9]*-[0-9]*', file)
    	if m is not None:
    		print m.group()
    		with open(file, 'r+') as f: 
				lines = []
				flag = 0 
				for line in f: 
					lines.append(line)
					#print line
					if line[:3] == '---' and flag != 1:
						flag = 1
						lines.append("date: %s" % m.group() + '\n')
						print file
						print 'date: %s' % m.group()
				f.seek(0)
				for line in lines: 
					f.write(line) 
          #f = open(path+"/"+file); #打开文件
          #iter_f = iter(f); #创建迭代器
          #str = ""
          #for line in iter_f: #遍历文件，一行行遍历，读取文本
          #    str = str + line
          #s.append(str) #每个文件的文本存到list中
