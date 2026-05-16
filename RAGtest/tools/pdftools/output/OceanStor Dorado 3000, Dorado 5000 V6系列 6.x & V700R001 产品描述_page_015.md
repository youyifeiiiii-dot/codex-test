# OceanStor Dorado 3000, Dorado 5000 V6系列 6.x & V700R001 产品描述 - Page 15

> Source PDF: `OceanStor Dorado 3000, Dorado 5000 V6系列 6.x & V700R001 产品描述.pdf`
> Page: 15 / 225

OceanStor Dorado 3000, Dorado 5000 V6 系列
产品描述
2 产品特点
文档版本15 (2025-09-30)
版权所有 © 华为技术有限公司
2
2 产品特点
OceanStor Dorado 采用全新的硬件结构，基于全闪存深度优化的软件架构，结合多种
高级数据应用和数据保护技术，使存储系统具有高性能、高稳定性、高可扩展性、高
可靠性和高可用性等特点，满足大中型企业对存储产品的各种要求。并且OceanStor
Dorado 采用SAN/NAS 一体化设计，不需要单独的NAS 网关设备，一套软硬件同时
支持SAN 和NAS，支持NFS、CIFS、S3、HTTP、FTP、FC（支持基于SCSI 接口的
FC-SCSI 协议和基于NVMe 接口的FC-NVMe 协议）、iSCSI、NVMe over RoCE 等协
议。SAN 和NAS 均支持多控的Scale-out 技术，主机可以从任意1 个控制器上的前端
主机端口访问任意1 个LUN 或文件系统。
￿
6.1.0 及后续版本支持文件业务。
￿
对于6.1.0 版本，OceanStor Dorado 5300 V6 暂不支持文件业务。
￿
对于6.1.2~6.1.5 版本，OceanStor Dorado 5300 V6（每控64GB 内存）不支持文件业务，
OceanStor Dorado 5300 V6（每控128GB 内存）支持文件业务。
￿
对于6.1.6 及后续版本，OceanStor Dorado 5300 V6（每控64GB 内存）和OceanStor
Dorado 5300 V6（每控128GB 内存）都支持文件业务。
￿
FC-NVMe 协议与应用场景和网络生态成熟度强相关，6.1.5~V700R001C01 版本部分接口模
块不支持FC-NVMe 协议，具体支持情况请联系华为技术工程师；V700R001C10 及后续版
本FC 接口模块均支持FC-NVMe 协议。
高性能
OceanStor Dorado 采用专为闪存设计的FlashLink®技术，具备高IOPS
（Input/Output Operations Per Second）并发能力，同时保持稳定的低时延。
FlashLink®技术的核心是通过一系列针对闪存介质的算法优化技术，实现了控制器板载
CPU 和SSD 板载专用CPU 的联动，保障了SSD 算法在不同CPU 之间的协同，实现
系统的高性能和高可靠。FlashLink®技术主要包含以下关键技术：
