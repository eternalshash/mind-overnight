import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os
import re
import subprocess

# ----------------- DOCUMENT TEXT DEFINITIONS -----------------

doc_title = "ECE 473 / 573: Cloud Computing and Cloud Native Systems"
doc_subtitle = "Homework 05: Managed Cloud Services (Container Orchestration with Google Kubernetes Engine)"

meta_text = [
    ("Student Name", "Shashwat Choudhry"),
    ("Student ID", "A20507277"),
    ("Course", "ECE 473 / 573: Cloud Computing and Cloud Native Systems (Fall 2026)"),
    ("Assignment", "Homework 05: Managed Cloud Services Investigation"),
    ("Due Date", "November 15, 2026 (Sunday, end of day Chicago time)")
]

# Section 1: Cloud Provider and Managed Service Name
sec1_title = "1. Selected Cloud Provider and Managed Service"
sec1_p1 = (
    "The selected public cloud provider is Google Cloud Platform (GCP), and the investigated managed service is "
    "Google Kubernetes Engine (GKE). Google originally designed the underlying container orchestration architecture "
    "based on over a decade of internal experience running the Borg and Omega cluster management systems. In 2014, "
    "Google open-sourced this technology as Kubernetes under the Cloud Native Computing Foundation (CNCF). In 2015, "
    "Google launched Google Kubernetes Engine as the industry first enterprise-grade managed Kubernetes service. "
    "Today, GKE stands as the flagship reference implementation of managed container orchestration in the cloud."
)

# Section 2: Kind of Service Provided and Architectural Differences from Lecture
sec2_title = "2. Service Nature and Comparison with Unmanaged (Vanilla) Kubernetes"
sec2_p1 = (
    "Google Kubernetes Engine provides Container Orchestration as a Managed Service (Platform as a Service / Container "
    "as a Service). GKE automates the full operational lifecycle of containerized workloads packaged as Open Container "
    "Initiative (OCI) compliant images. The platform handles scheduling, service discovery, internal and external load "
    "balancing, container health checking, automatic healing, progressive rolling updates, horizontal resource scaling, "
    "and persistent storage volume provisioning."
)

sec2_sub1 = "Core Architectural Comparison: Lecture Concepts vs. Managed Reality"
sec2_p2 = (
    "In the lecture syllabus, container orchestration was introduced through the foundational architecture of open-source "
    "Kubernetes. A standard unmanaged cluster splits into two decoupled planes: the Control Plane (etcd distributed key-value "
    "store, kube-apiserver, kube-scheduler, kube-controller-manager, and cloud-controller-manager) and the Data Plane "
    "(worker nodes executing kubelet, kube-proxy, and a container runtime such as containerd).\n\n"
    "When deploying vanilla Kubernetes manually (for example, on bare metal or bare virtual machine instances via kubeadm), "
    "the systems engineer assumes complete operational responsibility for:\n"
    "• Control Plane High Availability: Configuring multi-node etcd clusters, managing raft consensus, executing scheduled "
    "database snapshots, managing transaction log compaction, and performing disaster recovery.\n"
    "• Security and Lifecycle Management: Generating root certificate authorities, rotating TLS keys across cluster components, "
    "and applying operating system security patches to master hosts.\n"
    "• Upgrades and Maintenance: Executing sequential control plane binary upgrades across minor versions and draining worker "
    "nodes manually to prevent service interruptions."
)

sec2_sub2 = "Major Enhancements and Operational Distinctions in GKE"
sec2_p3 = (
    "Google Kubernetes Engine fundamentally transforms this operational model by offloading the entire control plane burden "
    "to Google Site Reliability Engineers (SREs). GKE introduces four major structural advancements over unmanaged Kubernetes:\n\n"
    "1. Fully Managed and Replicated Control Plane: Google provisions, provisions networking for, monitors, and scales the "
    "control plane automatically. In GKE, master nodes run in a dedicated Google-owned VPC network that connects to the user "
    "VPC via VPC Network Peering. Master components are shielded behind internal load balancers with automated etcd encryption, "
    "continuous automated backups, and guaranteed availability service level agreements (99.95% uptime for zonal clusters and "
    "99.99% for regional clusters).\n\n"
    "2. Node Auto-Repair and Node Auto-Upgrade: GKE implements automated background health agents on worker nodes. When a node "
    "fails continuous health checks (such as kernel deadlocks, disk corruption, or network partitioning) for a specified period, "
    "GKE automatically drains the node, terminates the underlying Compute Engine instance, and provisions an identical healthy "
    "node. During version upgrades, GKE offers configurable release channels (Rapid, Regular, Stable) and executes automated "
    "rolling surge upgrades or blue-green pool transitions without human intervention.\n\n"
    "3. GKE Autopilot vs. GKE Standard Operational Modes: In GKE Standard mode, users retain administrative control over node "
    "pools (selecting VM machine families, custom kernel settings, and disk sizes), while Google manages the control plane. "
    "In GKE Autopilot mode, Google manages the entire cluster end-to-end, including all worker nodes. Users interact strictly "
    "with Kubernetes declarative API objects (Deployments, StatefulSets, Services), eliminating the concept of node administration "
    "entirely and enforcing Google production security hardening by default.\n\n"
    "4. Deep Cloud-Native Integration: GKE integrates natively with Google Cloud infrastructure services. Worker pods receive "
    "direct, routable private IP addresses from the VPC subnet via alias IP ranges (VPC-native networking), avoiding secondary "
    "overlay encapsulation overhead. Workload Identity allows Kubernetes service accounts to bind directly to Google Cloud IAM "
    "roles, eliminating the need to store long-lived service account JSON keys inside container secrets. Network Endpoint Groups "
    "(NEGs) enable Google Cloud external Application Load Balancers to route ingress HTTP traffic directly to container pods "
    "without traversing intermediate kube-proxy node-port hops."
)

# Section 3: Horizontal Autoscaling
sec3_title = "3. Automatic Horizontal Scaling Capabilities"
sec3_p1 = (
    "Automatic horizontal scale-out is one of the most powerful capabilities of Google Kubernetes Engine. Rather than "
    "relying on a single scaling mechanism, GKE implements a multi-tier, synchronized horizontal scaling architecture that "
    "operates simultaneously at both the container workload tier and the underlying compute infrastructure tier."
)

sec3_sub1 = "Workload Tier: Horizontal Pod Autoscaler (HPA)"
sec3_p2 = (
    "At the application layer, GKE leverages the Kubernetes Horizontal Pod Autoscaler (HPA) to dynamically increase or "
    "decrease the number of Pod replicas assigned to a Deployment, ReplicaSet, or StatefulSet as demand fluctuates:\n"
    "• Resource-Based Autoscaling: By default, the HPA controller queries the Kubernetes Metrics Server every 15 seconds to "
    "compute real-time CPU consumption and memory consumption across existing pods. If the observed average consumption exceeds "
    "a declared target percentage of the requested container resources, HPA expands the replica count.\n"
    "• Custom and External Metrics Autoscaling: GKE integrates with Google Cloud Monitoring through the Custom Metrics "
    "Stackdriver Adapter. This allows applications to scale horizontally based on rich domain-specific signals, such as incoming "
    "HTTP request rates, active socket connections, latency percentiles, or the message backlog depth of a Google Cloud "
    "Pub/Sub subscription topic.\n"
    "• Scaling Formula and Stabilization: The autoscaler determines desired pod replicas using the proportional relationship:\n"
    "      Desired Replicas = ceil [ Current Replicas * ( Current Metric Value / Target Metric Value ) ]\n"
    "To prevent rapid fluctuation (thrashing) under volatile traffic spikes, GKE provides configurable stabilization windows "
    "and rate-limiting rules that control the maximum velocity of scale-up and scale-down transitions."
)

sec3_sub2 = "Infrastructure Tier: Cluster Autoscaler (CA) and Node Auto-Provisioning"
sec3_p3 = (
    "When HPA scales out pod replicas during heavy demand, total cluster resource requests may exceed the aggregate compute "
    "capacity of the existing worker nodes. In an unmanaged cluster, new pods would sit permanently in a Pending state due to "
    "insufficient CPU or memory. GKE solves this through automated infrastructure expansion:\n"
    "• Cluster Autoscaler (CA): The GKE Cluster Autoscaler continuously listens for pods flagged as Pending with FailedScheduling "
    "events. CA inspects the pod scheduling constraints (including node selectors, resource requests, taints, tolerations, and "
    "pod affinity rules), calculates the exact number of Compute Engine VM instances required to satisfy the shortfall, and "
    "automatically provisions new nodes into the target node pool up to a user-defined maximum limit.\n"
    "• Automated Infrastructure Scale-Down: When workload traffic subsides and HPA terminates redundant pod replicas, CA detects "
    "worker nodes whose capacity is no longer necessary. After a stabilization period (typically 10 minutes of low load), "
    "CA safely cordons the node, evicts remaining pods onto other active hosts, and deletes the empty Compute Engine VM instances, "
    "ensuring that the organization stops paying for idle hardware.\n"
    "• Node Auto-Provisioning (NAP): An advanced extension of Cluster Autoscaler that dynamically instantiates entirely new node "
    "pools with optimal machine types (for instance, dynamically provisioning GPU-enabled or high-memory instances) when pending "
    "pods cannot fit on any existing node pool configurations.\n"
    "• Zero-Configuration Scaling in Autopilot Mode: For clusters running in GKE Autopilot mode, infrastructure scaling is "
    "completely seamless. When HPA increases pod replicas, Google underlying control systems provision the exact compute and "
    "memory capacity required behind the scenes without requiring administrators to configure node pools, minimum node counts, "
    "or scaling boundaries."
)

# Section 4: Pricing Model
sec4_title = "4. Detailed Pricing Model Breakdown"
sec4_p1 = (
    "Google Kubernetes Engine employs a transparent, modular pricing model based on control plane management, compute "
    "infrastructure consumption (differentiated by GKE Standard and GKE Autopilot modes), persistent storage allocations, "
    "and network egress bandwidth."
)

sec4_sub1 = "1. Cluster Management Fee (Control Plane)"
sec4_p2 = (
    "GKE charges a flat cluster management fee of $0.10 per cluster per hour, billed in one-second increments. This fee covers "
    "Google round-the-clock management of the Kubernetes control plane, high-availability multi-zone etcd replication, automated "
    "backups, and SLA guarantees.\n"
    "• Google Cloud Free Tier Allowance: Google provides a monthly billing credit of $74.40 per billing account. Because 744 hours "
    "at $0.10 per hour equals $74.40, this credit completely offsets the management fee for one zonal or regional cluster each "
    "month. Consequently, single-cluster production deployments and development environments incur zero control plane fees. "
    "Additional concurrent clusters are billed at the standard $0.10 per hour rate."
)

sec4_sub2 = "2. Compute Infrastructure Pricing: Standard Mode vs. Autopilot Mode"
sec4_p3 = (
    "GKE provides two contrasting billing models for compute capacity:\n\n"
    "A. GKE Standard Mode (Node-Based Billing):\n"
    "• In Standard mode, customers pay for the underlying Google Compute Engine virtual machine instances provisioned in worker "
    "node pools, regardless of whether container pods fully populate those nodes.\n"
    "• Pricing follows standard Compute Engine rates based on selected machine series (such as general-purpose E2, compute-optimized "
    "C2, or memory-optimized M2), measured per second with a one-minute minimum charge.\n"
    "• Cost Optimization Options: Customers can deploy Spot VMs (excess Google capacity available at a 60% to 91% discount "
    "for fault-tolerant workloads) or purchase one-year and three-year Committed Use Discounts (CUDs) to achieve discounts up to 57%.\n\n"
    "B. GKE Autopilot Mode (Pod-Based Resource Billing):\n"
    "• Autopilot eliminates instance-based billing. Customers do not pay for worker VM instances, operating system overhead, or "
    "unused buffer capacity.\n"
    "• Billing is calculated per second based on the exact compute resources requested by actively running pods:\n"
    "  - vCPU: Billed at approximately $0.0445 per vCPU-hour for regular pods, or $0.0089 per vCPU-hour on Spot pods.\n"
    "  - Memory: Billed at approximately $0.0049 per GB-hour for regular pods, or $0.00098 per GB-hour on Spot pods.\n"
    "  - Ephemeral Storage: Billed at approximately $0.000055 per GB-hour for storage requested beyond the default 1 GB allocation.\n"
    "• Autopilot provides a financially backed 99.9% availability SLA for pods spanning multiple zones."
)

sec4_sub3 = "3. Persistent Storage and Networking Bandwidth Fees"
sec4_p4 = (
    "Workloads deployed on GKE incur standard ancillary Google Cloud resource charges:\n"
    "• Persistent Storage: Persistent Volumes provisioned via Kubernetes StorageClasses use Google Cloud Persistent Disks. Standard "
    "hard disk storage (pd-standard) costs approximately $0.040 per GB-month, Balanced SSD storage (pd-balanced) costs $0.100 per "
    "GB-month, and high-performance SSD storage (pd-ssd) costs $0.170 per GB-month.\n"
    "• Network Egress: All ingress data traffic into GKE is free. Data transfer between pods within the same zone is free. Inter-zone "
    "network traffic within the same region costs $0.01 per GB. External internet egress is billed according to standard Google "
    "Cloud tiered rates (starting at $0.12 per GB for standard worldwide internet egress).\n"
    "• Load Balancing: When exposing services externally using Service type LoadBalancer or GKE Ingress, standard Google Cloud "
    "forwarding rule charges apply (approximately $0.025 per hour for the first five forwarding rules plus data processing charges)."
)

sec5_title = "5. Summary and Engineering Takeaways"
sec5_p1 = (
    "Managed container orchestration through Google Kubernetes Engine shifts operational focus from low-level infrastructure "
    "maintenance toward application development and delivery. By offloading etcd state replication, security patching, and "
    "control plane scaling to Google, engineering teams eliminate substantial operational overhead. Furthermore, GKE "
    "multi-tiered autoscaling combines application-level agility via HPA with elastic compute scaling via Cluster Autoscaler, "
    "ensuring high service availability under surging load while minimizing unnecessary expenditure during quiet operational periods."
)

# Tables data
# Table 1: Feature comparison
table1_headers = [
    "Capability / Metric",
    "Self-Managed (Vanilla) Kubernetes",
    "GKE Standard Mode",
    "GKE Autopilot Mode"
]
table1_rows = [
    [
        "Control Plane Management",
        "Manual deployment, patching, and maintenance of etcd and apiservers",
        "Fully managed, monitored, and auto-upgraded by Google SREs",
        "Fully managed, monitored, and auto-upgraded by Google SREs"
    ],
    [
        "Worker Node Management",
        "Manual OS provisioning, kubelet installation, and patch administration",
        "Automated node provisioning, node auto-repair, and node auto-upgrade",
        "Fully managed by Google; zero node administration or VM configuration"
    ],
    [
        "Horizontal Pod Scaling (HPA)",
        "Supported via manual Metrics Server installation and configuration",
        "Native, fully integrated with Cloud Monitoring custom metrics",
        "Native, fully integrated with Cloud Monitoring custom metrics"
    ],
    [
        "Infrastructure Autoscaling",
        "Manual setup of open-source Cluster Autoscaler binary and cloud credentials",
        "Native Cluster Autoscaler with automated Node Auto-Provisioning (NAP)",
        "Fully autonomous; infrastructure provisions dynamically to fit pods"
    ],
    [
        "Cloud Network Integration",
        "Overlay CNI plugin required (e.g. Flannel, Calico) with NAT overhead",
        "VPC-native alias IPs; direct pod routing via Network Endpoint Groups",
        "VPC-native alias IPs; direct pod routing via Network Endpoint Groups"
    ],
    [
        "Security and Identity",
        "Manual TLS certificate rotation and static service account token secrets",
        "Workload Identity maps Kubernetes Service Accounts to GCP IAM roles",
        "Workload Identity enforced by default with hardened security posture"
    ],
    [
        "Service Level Agreement (SLA)",
        "No SLA (100% customer responsibility)",
        "99.95% (zonal) / 99.99% (regional) for control plane",
        "99.99% for control plane; 99.9% for multi-zone pod workloads"
    ]
]

# Table 2: Scaling mechanisms
table2_headers = [
    "Scaling Mechanism",
    "Operational Layer",
    "Trigger Signals",
    "Action Executed",
    "Primary Benefit"
]
table2_rows = [
    [
        "Horizontal Pod Autoscaler (HPA)",
        "Application (Workload)",
        "CPU/Memory usage percentage, HTTP request rate, Cloud Pub/Sub queue depth",
        "Increases or decreases pod replica count in Deployment or StatefulSet",
        "Rapidly adapts application processing capacity to real-time client demand"
    ],
    [
        "Cluster Autoscaler (CA)",
        "Infrastructure (Compute)",
        "Pending pods with FailedScheduling events due to compute shortfall",
        "Provisions additional Google Compute Engine VM instances to node pool",
        "Prevents pod starvation by expanding node capacity on demand"
    ],
    [
        "Node Auto-Provisioning (NAP)",
        "Infrastructure (Compute)",
        "Pending pods requiring machine shapes or accelerators not in existing pools",
        "Dynamically creates brand-new node pools with optimal machine types",
        "Eliminates manual pre-configuration of specialized hardware pools"
    ],
    [
        "Cluster Scale-Down",
        "Infrastructure (Compute)",
        "Worker nodes consistently idle or lightly loaded for longer than stabilization window",
        "Safely cordons, drains, and terminates idle Compute Engine VM instances",
        "Reduces infrastructure spending by eliminating waste during quiet periods"
    ]
]

# Table 3: Pricing summary
table3_headers = [
    "Billing Dimension",
    "GKE Standard Mode Pricing",
    "GKE Autopilot Mode Pricing",
    "Billing Notes and Optimization"
]
table3_rows = [
    [
        "Cluster Management Fee",
        "$0.10 per cluster per hour ($73.00 per month)",
        "$0.10 per cluster per hour ($73.00 per month)",
        "First cluster per billing account is free ($74.40 monthly credit applied)"
    ],
    [
        "Compute Infrastructure",
        "Billed per provisioned GCE VM instance (per second, 1-min minimum)",
        "Billed per running pod requested resources (vCPU, memory, storage per second)",
        "Autopilot charges only for pod requests; Standard charges for whole VM node"
    ],
    [
        "Compute Pricing Rates",
        "Standard GCE machine rates (e.g. E2, N2, C2 instance family pricing)",
        "Regular: ~$0.0445/vCPU-hr, ~$0.0049/GB-hr\nSpot: ~$0.0089/vCPU-hr, ~$0.00098/GB-hr",
        "Spot VMs offer 60% to 91% savings on fault-tolerant stateless workloads"
    ],
    [
        "Persistent Storage",
        "Standard Persistent Disk rates ($0.040-$0.170/GB-month)",
        "Standard Persistent Disk rates ($0.040-$0.170/GB-month)",
        "Dynamic volume provisioning via CSI drivers for Standard and SSD disks"
    ],
    [
        "Network Bandwidth",
        "Ingress free; inter-zone $0.01/GB; internet egress from $0.12/GB",
        "Ingress free; inter-zone $0.01/GB; internet egress from $0.12/GB",
        "Direct VPC routing minimizes unnecessary cross-zone data transfer hops"
    ]
]

# Validation assertions
all_text = " ".join([
    doc_title, doc_subtitle,
    sec1_title, sec1_p1,
    sec2_title, sec2_p1, sec2_sub1, sec2_p2, sec2_sub2, sec2_p3,
    sec3_title, sec3_p1, sec3_sub1, sec3_p2, sec3_sub2, sec3_p3,
    sec4_title, sec4_p1, sec4_sub1, sec4_p2, sec4_sub2, sec4_p3, sec4_sub3, sec4_p4,
    sec5_title, sec5_p1
] + [cell for row in table1_rows for cell in row]
  + [cell for row in table2_rows for cell in row]
  + [cell for row in table3_rows for cell in row]
)

# Verify zero em/en dashes
dashes = re.findall(r'[—–]', all_text)
assert len(dashes) == 0, f"Found dashes: {dashes}"

# Verify zero banned words
banned_words = ['delve', 'utilize', 'tapestry', 'moreover', 'ultimately']
for bw in banned_words:
    assert bw not in all_text.lower(), f"Found banned word '{bw}' in text!"

print("Validation passed: 0 dashes, 0 banned words.")

# ----------------- BUILD DOCX DOCUMENT -----------------

doc = docx.Document()

# 1-inch margins
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Configure Default Normal Style
style = doc.styles['Normal']
font = style.font
font.name = 'Times New Roman'
font.size = Pt(12)
font.color.rgb = RGBColor(0, 0, 0)

COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_NAVY = RGBColor(0, 31, 63)        # #001F3F
HEX_NAVY = "001F3F"
HEX_BORDER_GRAY = "D0D7DE"
HEX_BG_LIGHT = "F8F9FA"
HEX_TH_BG = "001F3F"

def add_header(title, subtitle=""):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(title)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15.5)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY
    
    if subtitle:
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_before = Pt(2)
        p2.paragraph_format.space_after = Pt(6)
        r2 = p2.add_run(subtitle)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(12)
        r2.font.italic = True
        r2.font.color.rgb = RGBColor(70, 70, 70)

def add_meta(lines):
    for label, val in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.15
        r1 = p.add_run(label + ": ")
        r1.font.name = 'Times New Roman'
        r1.font.bold = True
        r1.font.size = Pt(11.5)
        r1.font.color.rgb = COLOR_NAVY
        r2 = p.add_run(val)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11.5)
        r2.font.color.rgb = COLOR_BLACK

def add_sec_title(title_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(title_str)
    r.font.name = 'Times New Roman'
    r.font.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = COLOR_NAVY

def add_sub_title(title_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title_str)
    r.font.name = 'Times New Roman'
    r.font.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = COLOR_NAVY

def add_para(text_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text_str)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(12)
    r.font.color.rgb = COLOR_BLACK

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def style_table(table, col_widths, headers, data_rows):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], HEX_TH_BG)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.runs[0]
        r.font.name = 'Times New Roman'
        r.font.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(255, 255, 255)
    
    # Data rows
    for r_idx, row_data in enumerate(data_rows):
        row_cells = table.add_row().cells
        bg_col = "F8F9FA" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_col)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            if len(p.runs) > 0:
                p.runs[0].font.name = 'Times New Roman'
                p.runs[0].font.size = Pt(9.5)
                p.runs[0].font.color.rgb = COLOR_BLACK

    # Set column widths
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = Inches(width)

# Assemble Document
add_header(doc_title, doc_subtitle)
add_meta(meta_text)

# Section 1
add_sec_title(sec1_title)
add_para(sec1_p1)

# Section 2
add_sec_title(sec2_title)
add_para(sec2_p1)
add_sub_title(sec2_sub1)
add_para(sec2_p2)

# Table 1: Feature comparison
t1 = doc.add_table(rows=1, cols=4)
style_table(t1, [1.4, 1.7, 1.7, 1.7], table1_headers, table1_rows)

add_sub_title(sec2_sub2)
add_para(sec2_p3)

# Section 3
add_sec_title(sec3_title)
add_para(sec3_p1)
add_sub_title(sec3_sub1)
add_para(sec3_p2)

# Table 2: Scaling mechanisms
t2 = doc.add_table(rows=1, cols=5)
style_table(t2, [1.4, 1.1, 1.5, 1.3, 1.2], table2_headers, table2_rows)

add_sub_title(sec3_sub2)
add_para(sec3_p3)

# Section 4
add_sec_title(sec4_title)
add_para(sec4_p1)
add_sub_title(sec4_sub1)
add_para(sec4_p2)
add_sub_title(sec4_sub2)
add_para(sec4_p3)

# Table 3: Pricing summary
t3 = doc.add_table(rows=1, cols=4)
style_table(t3, [1.4, 1.7, 1.7, 1.7], table3_headers, table3_rows)

add_sub_title(sec4_sub3)
add_para(sec4_p4)

# Section 5
add_sec_title(sec5_title)
add_para(sec5_p1)

# Output Paths
out_dir = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473"
desktop_dir = "/Users/schoudhry/Desktop"

out_docx = os.path.join(out_dir, "ECE473_HW05_ShashwatChoudhry.docx")
desktop_docx = os.path.join(desktop_dir, "ECE473_HW05_ShashwatChoudhry.docx")

doc.save(out_docx)
doc.save(desktop_docx)
print(f"Saved DOCX to {out_docx} and {desktop_docx}")

# Convert to Apple Pages using AppleScript
desktop_pages = os.path.join(desktop_dir, "ECE473_HW05_ShashwatChoudhry.pages")
out_pages = os.path.join(out_dir, "ECE473_HW05_ShashwatChoudhry.pages")

applescript_pages = f'''
tell application "Pages"
    activate
    open POSIX file "{desktop_docx}"
    delay 2
    set frontDoc to front document
    save frontDoc in POSIX file "{desktop_pages}"
    delay 1
    save frontDoc in POSIX file "{out_pages}"
end tell
'''

try:
    res = subprocess.run(["osascript", "-e", applescript_pages], capture_output=True, text=True, timeout=40)
    print("Pages conversion output:", res.stdout, res.stderr)
    print(f"Generated Pages document: {desktop_pages}")
except Exception as e:
    print(f"Pages error: {e}")

# Export PDF as well for complete records
desktop_pdf = os.path.join(desktop_dir, "ECE473_HW05_ShashwatChoudhry.pdf")
out_pdf = os.path.join(out_dir, "ECE473_HW05_ShashwatChoudhry.pdf")

applescript_pdf = f'''
tell application "Pages"
    activate
    set frontDoc to front document
    export frontDoc to POSIX file "{desktop_pdf}" as PDF
    delay 1
    export frontDoc to POSIX file "{out_pdf}" as PDF
end tell
'''

try:
    res_pdf = subprocess.run(["osascript", "-e", applescript_pdf], capture_output=True, text=True, timeout=40)
    print("PDF export output:", res_pdf.stdout, res_pdf.stderr)
    print(f"Generated PDF: {desktop_pdf}")
except Exception as e:
    print(f"PDF error: {e}")

print("ECE473 Homework 05 successfully created and active in Apple Pages!")
