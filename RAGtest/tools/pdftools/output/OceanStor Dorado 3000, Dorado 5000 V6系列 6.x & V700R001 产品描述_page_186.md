# OceanStor Dorado 3000, Dorado 5000 V6系列 6.x & V700R001 产品描述 - Page 186

> Source PDF: `OceanStor Dorado 3000, Dorado 5000 V6系列 6.x & V700R001 产品描述.pdf`
> Page: 186 / 225

OceanStor Dorado 3000, Dorado 5000 V6 系列
产品描述
4 软件架构
文档版本15 (2025-09-30)
版权所有 © 华为技术有限公司
173
软件组件
功能说明
表4-3
维护终端软件用于系统配置与维护。用户可以通过维护终端的
SmartKit、DME IQ 等软件对存储系统进行配置和维护。
表4-4
应用服务器端软件可与存储系统通信，从而使双方能够配合执行
某些操作。应用服务器端软件包括OceanStor BCManager 和
UltraPath。
存储系统端软件说明如表4-2 所示。
表4-2 存储系统端软件说明
软件集合名
称
软件名称
功能说明
OceanStor
OS 内核
-
基于欧拉操作系统定制，管理硬件和支撑存储
业务软件的运行。
OceanStor
DeviceManager
OceanStor DeviceManager 是华为技术有限
公司推出的集成存储管理平台。OceanStor
DeviceManager 可以轻松便捷地配置、管理
和维护存储设备。
SNMPab
存储系统支持通过SNMP 协议与第三方管理
软件对接，并通过MIB 接口对外提供第三方
管理软件所支持的功能。支持SNMP 协议的
网管软件种类很多，用户可自行选用。
CLIc
存储系统支持CLI 进行管理配置。可以使用第
三方终端软件通过串口或者管理网口（使用
SSH 协议）登录和使用存储系统CLI 界面。
管理功能控
制软件
Syslog
存储系统支持向第三方发送告警信息。Syslog
软件能够接收并存储这些信息。第三方的
Syslog 软件种类很多，用户可自行选用。
基本功能控
SCSI 软件模块
处理主机接口协议的传输层协议，可实现
SCSI 命令的状态管理和前后调度，并负责
