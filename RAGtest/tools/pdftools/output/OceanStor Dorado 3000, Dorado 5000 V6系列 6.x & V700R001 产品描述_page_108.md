# OceanStor Dorado 3000, Dorado 5000 V6系列 6.x & V700R001 产品描述 - Page 108

> Source PDF: `OceanStor Dorado 3000, Dorado 5000 V6系列 6.x & V700R001 产品描述.pdf`
> Page: 108 / 225

OceanStor Dorado 3000, Dorado 5000 V6 系列
产品描述
3 硬件架构
文档版本15 (2025-09-30)
版权所有 © 华为技术有限公司
95
指示灯
状态和说明
数据。
￿绿色，常亮：端口为ETH 类型，端口已连接。
￿绿色，闪烁（2Hz）：端口为ETH 类型，正在传
输数据。
￿黄色，常亮：端口光模块故障或光模块不匹配。
￿灭：端口没有连接。
￿
如果主机侧使用iSCSI 协议，SmartIO 端口的MTU 值必须与主机侧的MTU 值保持一致。
￿
如果SmartIO 端口为10Gbit/s ETH 和25Gbit/s ETH，推荐将主机侧HBA 卡的LRO 功能保
持开启。不同的操作系统提供不同的查询和开启操作，下面列举三种常见的操作系统的查询
和开启操作。如果主机侧HBA 卡不支持LRO 功能，推荐采用Jumbo 帧方式（即将主机、
交换机和存储系统SmartIO 接口模块的MTU 值设置为推荐值9000）。
−
Linux 系统：执行命令ethtool -k ethx 查看LRO 功能是否开启；执行命令ethtool -K
ethx lro on 开启LRO 功能。
−
Windows 系统：在设备管理器的网卡设备属性中查看并设置。
−
ESXi 系统：执行命令esxcfg-advcfg -g /Net/TcpipDefLROEnabled 查看LRO 功能是
否开启；执行命令esxcfg-advcfg -s 1 /Net/TcpipDefLROEnabled 开启LRO 功能。
3.7.10 12Gb SAS 接口模块
12Gb SAS 接口模块通过级联端口连接控制框和SAS 硬盘框，是控制框和SAS 硬盘框
之间进行数据传输的连接点。
OceanStor Dorado 5500 V6（NVMe）、OceanStor Dorado 5600 V6（NVMe）不支持12Gb
SAS 级联模块。
功能
12Gb SAS 接口模块提供4 个传输速率为12Gbit/s 的mini SAS HD 级联端口，通过
mini SAS HD 线缆与存储系统的后端2U SAS 硬盘框连接。当连接的设备传输速率低
于级联端口速率时，级联端口将自动适应传输速率，以保证数据传输通道的连通性和
数据传输速率的一致性。
