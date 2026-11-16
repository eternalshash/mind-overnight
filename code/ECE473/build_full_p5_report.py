import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os
import subprocess

# ----------------- STYLING CONSTANTS -----------------
# Strict adherence to field notes guidelines:
# - Black text Times New Roman size 11 for body, 1.15 line spacing, 1-inch margins
# - Accent tables in dark blue (#001F3F / #002060)
# - No banned buzzwords ('delve', 'utilize', 'tapestry', 'moreover', 'ultimately')
# - No em/en dashes (strictly use hyphens or clean punctuation)

COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_NAVY = RGBColor(0, 31, 63)       # #001F3F Deep Navy Accent
COLOR_MUTED = RGBColor(70, 70, 70)
HEX_NAVY = "001F3F"
HEX_LIGHT_BG = "F4F6F9"
HEX_BORDER = "D0D7DE"
HEX_WHITE = "FFFFFF"

doc = docx.Document()

for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

style_normal = doc.styles['Normal']
style_normal.font.name = 'Times New Roman'
style_normal.font.size = Pt(11)
style_normal.font.color.rgb = COLOR_BLACK
style_normal.paragraph_format.line_spacing = 1.15
style_normal.paragraph_format.space_after = Pt(4)

def add_header(title, subtitle):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15.5)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p2.paragraph_format.space_before = Pt(1)
    p2.paragraph_format.space_after = Pt(6)
    r2 = p2.add_run(subtitle)
    r2.font.name = 'Times New Roman'
    r2.font.size = Pt(11)
    r2.font.italic = True
    r2.font.color.rgb = COLOR_MUTED

def add_meta(lines):
    for label, val in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.15
        r1 = p.add_run(label + ": ")
        r1.font.name = 'Times New Roman'
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = COLOR_NAVY
        r2 = p.add_run(val)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = COLOR_BLACK

def add_sec_title(title_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(title_str)
    r.font.name = 'Times New Roman'
    r.font.bold = True
    r.font.size = Pt(12.5)
    r.font.color.rgb = COLOR_NAVY

def add_sub_title(title_str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title_str)
    r.font.name = 'Times New Roman'
    r.font.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = COLOR_NAVY

def add_para(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(11)
    r.font.color.rgb = COLOR_BLACK
    return p

def add_bullet(bold_prefix, text):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r1 = p.add_run(bold_prefix + " ")
        r1.font.name = 'Times New Roman'
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = COLOR_NAVY
    r2 = p.add_run(text)
    r2.font.name = 'Times New Roman'
    r2.font.size = Pt(11)
    r2.font.color.rgb = COLOR_BLACK
    return p

def add_code_block(code_text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.5)

    cell = table.cell(0, 0)
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{HEX_LIGHT_BG}"/>')
    cell._tc.get_or_add_tcPr().append(shd)

    b = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
        f'<w:left w:val="single" w:sz="18" w:space="0" w:color="{HEX_NAVY}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
        f'</w:tcBorders>'
    )
    cell._tc.get_or_add_tcPr().append(b)

    mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="100" w:type="dxa"/>'
        f'<w:left w:w="160" w:type="dxa"/>'
        f'<w:bottom w:w="100" w:type="dxa"/>'
        f'<w:right w:w="160" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    cell._tc.get_or_add_tcPr().append(mar)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.05
    r = p.add_run(code_text)
    r.font.name = 'Courier New'
    r.font.size = Pt(9.0)
    r.font.color.rgb = COLOR_BLACK

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(3)

def add_image_centered(img_path, width_in, caption_text=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(img_path, width=Inches(width_in))

    if caption_text:
        pc = doc.add_paragraph()
        pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pc.paragraph_format.space_before = Pt(1)
        pc.paragraph_format.space_after = Pt(6)
        rc = pc.add_run(caption_text)
        rc.font.name = 'Times New Roman'
        rc.font.size = Pt(9.5)
        rc.font.italic = True
        rc.font.color.rgb = COLOR_NAVY

def style_table(table, col_widths, headers, rows):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].width = Inches(col_widths[i])
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(title)
        r.font.name = 'Times New Roman'
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{HEX_NAVY}"/>')
        hdr_cells[i]._tc.get_or_add_tcPr().append(shd)

    for r_idx, row_data in enumerate(rows):
        row_cells = table.add_row().cells
        bg_color = HEX_LIGHT_BG if r_idx % 2 == 1 else HEX_WHITE
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].width = Inches(col_widths[c_idx])
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(9.0)
            r.font.color.rgb = COLOR_BLACK
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
            row_cells[c_idx]._tc.get_or_add_tcPr().append(shd)

    for row in table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            b = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/>'
                f'</w:tcBorders>'
            )
            tcPr.append(b)

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)

# ----------------- DOCUMENT CONTENT -----------------

# Header
add_header("ECE 473 / 573: Cloud Computing and Cloud Native Systems",
           "Project 5 Report: Container Orchestration with Kubernetes")

add_meta([
    ("Student Name", "Shashwat Choudhry"),
    ("Student ID", "A20507277"),
    ("Course", "ECE 473 / 573 Cloud Computing and Cloud Native Systems (Fall 2026)"),
    ("Instructors", "Prof. Tianyang Fang and Prof. Jafar Saniie"),
    ("Due Date", "November 15, 2026 (Sunday, end of day Chicago time)")
])

# ==================== SECTION II ====================
add_sec_title("Section II: kind Cluster and Database Setup")

add_sub_title("1. Cluster, Cassandra Pods, and Postgres Pod Operational Evidence (1 point)")
add_para(
    "To establish the local Kubernetes development and testing topology, a multi-node cluster was instantiated using "
    "the kind (Kubernetes in Docker) engine. The underlying cluster configuration ('kind-cluster.yaml') defines a six-node "
    "topology comprising one control-plane node ('ece573-prj05-control-plane') and five dedicated worker nodes ('ece573-prj05-worker' "
    "through 'ece573-prj05-worker5'). Each Kubernetes node operates as an isolated Docker container executing the container runtime "
    "image 'kindest/node:v1.37.0'. Host port forwarding maps VM host ports 8080 and 8081 to NodePort entry points 30080 and 30081 on the "
    "control-plane node to facilitate local RESTful interaction."
)
add_para(
    "Following cluster initialization, the core database tiers defined in 'k8s/databases.yaml' were deployed. A three-replica "
    "Cassandra cluster was scheduled across the worker nodes via a StatefulSet, along with a dedicated single-replica PostgreSQL instance. "
    "Figure 1 provides comprehensive operational proof displaying the active kind cluster nodes, the underlying Docker container processes, "
    "and the healthy status of all database Pods and Services as reported by kubectl."
)

asset_dir = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/prj05_assets"
add_image_centered(os.path.join(asset_dir, "sec2_cluster_and_pods.png"), 6.5,
                   "Figure 1: Verification of kind cluster nodes, Docker container runtime hosts, and database Pods/Services.")

add_sub_title("2. Database Engine Health vs. Kubernetes Pod Infrastructure Status (1 point)")
add_para(
    "To verify that the database applications are operational at the protocol level, direct engine diagnostics were executed inside "
    "the running containers. For Apache Cassandra, 'nodetool status' was invoked within 'cassandra-0'. The ring membership diagnostic "
    "confirmed that all three nodes (10.244.1.3, 10.244.2.3, and 10.244.4.3) are in the 'UN' (Up and Normal) operational state, actively "
    "participating in Gossip protocol consensus, owning 16 virtual tokens each, and evenly balancing storage load within rack1 of datacenter1. "
    "For PostgreSQL, 'pg_isready' was executed against socket '/var/run/postgresql:5432', confirming that the database engine is actively "
    "accepting TCP connections for user 'marketplace' and catalog 'marketplace'. A direct SQL query via psql validated database readiness."
)

add_image_centered(os.path.join(asset_dir, "sec2_database_validation.png"), 6.5,
                   "Figure 2: Domain-level database engine validation via nodetool status (Cassandra) and pg_isready/psql (PostgreSQL).")

add_para(
    "Distinction between Pod Infrastructure Status and Application Engine Health:"
)
add_bullet(
    "• Kubernetes Pod Infrastructure Status (Question 1):",
    "Evaluates container runtime lifecycle and process supervisor state. The kubelet queries the container runtime interface (CRI) to confirm "
    "that the container process is running (PID 1 is alive) and that exit codes are zero. However, a container marked as 'Running' or passing basic "
    "TCP socket probes can still be functionally unresponsive if internal application threads are deadlocked, waiting on distributed locks, "
    "stalled during JVM garbage collection pauses, or failing during internal schema migrations."
)
add_bullet(
    "• Database Engine Operational Health (Question 2):",
    "Evaluates domain-specific protocol capability and distributed consensus. Running 'nodetool status' queries the internal Cassandra JMX "
    "endpoint to verify gossip ring membership, inter-node gossip heartbeat exchanges, cluster schema agreement, and token distribution. Running "
    "'pg_isready' and SQL queries confirms that PostgreSQL has completed Write-Ahead Log (WAL) replay, released startup locks, and is ready to parse, "
    "plan, and execute transactional SQL queries against the system catalog."
)

add_sub_title("3. Resource Allocation and Analysis of Kubernetes Requests vs. Limits (1 point)")
add_para(
    "Compute and storage resources configured in 'k8s/databases.yaml' govern scheduling density and runtime resource boundaries across "
    "the cluster nodes. Table 1 summarizes the exact resource specifications assigned to PostgreSQL and Cassandra."
)

res_headers = ["Resource Category", "PostgreSQL Specification", "Cassandra Specification", "Architectural Role & Scope"]
res_widths = [1.3, 1.5, 1.5, 2.2]
res_rows = [
    ["CPU Requests", "100m (0.1 core)", "250m (0.25 core)", "Guaranteed baseline compute scheduling allocation"],
    ["CPU Limits", "Unbounded (capacity bound)", "Unbounded (capacity bound)", "Permits CPU bursting during peak transaction spikes"],
    ["Memory Requests", "128 MiB", "768 MiB", "Baseline memory reservation for buffer pool / JVM heap"],
    ["Memory Limits", "512 MiB", "1024 MiB (1 GiB)", "Hard cgroup memory boundary enforced by kernel OOM killer"],
    ["Persistent Storage", "1 GiB (ReadWriteOnce)", "2 GiB per Pod (ReadWriteOnce)", "PersistentVolumeClaim dynamic volume allocation"]
]
t_res = doc.add_table(rows=1, cols=4)
style_table(t_res, res_widths, res_headers, res_rows)

add_para(
    "Architectural Distinction between 'Requests' and 'Limits':"
)
add_bullet(
    "• Resource Requests (resources.requests):",
    "Used exclusively by 'kube-scheduler' during the pod placement and filtering phase. A pod is scheduled onto a node only if that node has "
    "sufficient unallocated allocatable capacity to accommodate the sum of container requests. Requests establish the Quality of Service (QoS) "
    "tier (Burstable in this configuration). For CPU, requests configure the Linux Completely Fair Scheduler (CFS) share weighting (cpu.shares), "
    "ensuring guaranteed proportional CPU time under contention without artificially capping compute."
)
add_bullet(
    "• Resource Limits (resources.limits):",
    "Enforced at runtime by the Linux kernel control groups (cgroups). For memory, exceeding the limit triggers the kernel Out-Of-Memory (OOM) killer "
    "(exit status 137, OOMKilled), causing container termination and pod restart. In Cassandra, the limit (1024 MiB) safely accommodates the configured "
    "JVM heap (MAX_HEAP_SIZE=512M, HEAP_NEWSIZE=128M) plus off-heap direct byte buffers and thread stacks. For CPU, limits configure CFS bandwidth "
    "quota periods (cpu.cfs_quota_us); reaching a CPU limit results in thread throttling (latency degradation) rather than termination."
)

add_sub_title("4. Control Plane Inspection via crictl and Component Identification (1 point)")
add_para(
    "Because kind implements nested container architecture, executing 'crictl ps' via Docker inside 'ece573-prj05-control-plane' exposes the "
    "low-level container processes managed by the control plane containerd runtime. Figure 3 presents the terminal output of active containers."
)

add_image_centered(os.path.join(asset_dir, "sec2_control_plane_crictl.png"), 6.5,
                   "Figure 3: Inspection of core Kubernetes control plane containers running inside the control-plane kind node via crictl ps.")

add_para(
    "Key Kubernetes Control Plane Components Identified:"
)
add_bullet(
    "• kube-apiserver:",
    "The central administrative hub and master REST gateway for the entire Kubernetes control plane. It authenticates, authorizes, and validates all "
    "API requests from administrators (via kubectl), worker kubelets, and internal controllers, serving as the sole component with direct read/write access to etcd."
)
add_bullet(
    "• etcd:",
    "A distributed, strongly consistent, highly available key-value store implementing the Raft consensus algorithm. It holds the authoritative cluster state, "
    "declarative resource manifests, Service endpoints, secrets, and configuration maps across the entire Kubernetes lifecycle."
)

# ==================== SECTION III ====================
add_sec_title("Section III: Application Deployment and Microservice Architecture")

add_sub_title("1. Pod Naming Conventions: StatefulSets vs. Deployments (1 point)")
add_para(
    "The structural disparity in Pod naming stems from the fundamental distinction between Kubernetes workload controllers:"
)
add_bullet(
    "• StatefulSet Workloads (PostgreSQL and Cassandra):",
    "StatefulSets manage stateful applications requiring predictable network identities, ordered rollouts, and persistent storage bindings across restarts. "
    "Kubernetes assigns each Pod a deterministic ordinal index from 0 to N-1 (e.g., 'postgres-0', 'cassandra-0', 'cassandra-1', 'cassandra-2'). "
    "These deterministic names anchor stable DNS hostnames ('cassandra-0.cassandra') and dedicated PersistentVolumeClaim bindings ('data-cassandra-0') "
    "that remain invariant across pod rescheduling and host node failures."
)
add_bullet(
    "• Deployment Workloads (Login Service and Marketplace Service):",
    "Deployments manage completely stateless, horizontally scalable, interchangeable microservices. A Deployment creates an underlying ReplicaSet, which "
    "appends a pod template hash (e.g., '7d8cbb49bb') and a cryptographically randomized string (e.g., '97lzh', 'wds9m') to the pod name. "
    "Because stateless instances hold no local state and share no persistent storage volumes, individual pods are completely fungible and ephemeral."
)

add_sub_title("2. Database Service Discovery via CoreDNS (1 point)")
add_para(
    "Application microservices locate the backend database instances using Kubernetes CoreDNS internal service discovery:"
)
add_bullet(
    "• PostgreSQL Resolution (ClusterIP Service):",
    "The login and marketplace deployments specify 'POSTGRES_HOST=postgres' and 'POSTGRES_PORT=5432'. When an application initiates a connection, "
    "CoreDNS resolves the unqualified hostname 'postgres' to the virtual ClusterIP '10.96.51.3'. The Linux kernel iptables rules configured by kube-proxy "
    "intercept packets addressed to this virtual IP and transparently forward them to the backend endpoint of 'postgres-0' (10.244.3.2:5432)."
)
add_bullet(
    "• Cassandra Resolution (Headless Service):",
    "In 'k8s/databases.yaml', the Cassandra Service is configured with 'clusterIP: None' and 'publishNotReadyAddresses: true'. Because it is a headless Service, "
    "CoreDNS does not allocate a single virtual IP. Instead, it generates A/AAAA DNS records mapping individual StatefulSet ordinal FQDNs directly to "
    "pod IPs: 'cassandra-0.cassandra' -> 10.244.1.3, 'cassandra-1.cassandra' -> 10.244.2.3, and 'cassandra-2.cassandra' -> 10.244.4.3. The marketplace "
    "service receives 'CASSANDRA_CONTACT_POINTS=cassandra-0.cassandra,cassandra-1.cassandra,cassandra-2.cassandra'. The gocql driver resolves these names, "
    "initiates native CQL binary protocol connections on port 9042, and discovers full cluster topology via Cassandra system tables."
)

add_sub_title("3. RESTful Request Resolution and Load Balancing Behavior (1 point)")
add_para(
    "When an external client submits an HTTP REST request to the marketplace service, Kubernetes resolves and routes the traffic through a multi-stage pipeline:"
)
add_bullet(
    "1. Host Port Ingress:",
    "The client connects to VM localhost port 8080 (http://127.0.0.1:8080). In 'kind-cluster.yaml', extraPortMappings forwards host port 8080 to containerPort 30080 "
    "on the kind control-plane container."
)
add_bullet(
    "2. NodePort Service Interception:",
    "In 'k8s/apps.yaml', 'marketplace-service' is declared as a NodePort Service exposing port 8080 on nodePort 30080. The kube-proxy daemon on each node configures "
    "Linux netfilter/iptables chains (KUBE-NODEPORTS) to capture packets arriving on port 30080."
)
add_bullet(
    "3. Destination NAT (DNAT) and Endpoint Selection:",
    "The kube-proxy iptables rules maintain a list of ready Pod endpoints matching label 'app: marketplace-service'. Probabilistic iptables matching rules "
    "(using the 'statistic' module with mode random, e.g., 50% probability for the first pod, 100% for the remainder) apply DNAT to rewrite the destination IP "
    "to the chosen Pod IP (10.244.3.4 or 10.244.5.2)."
)
add_bullet(
    "• Will the request reach both marketplace pods?",
    "No. An HTTP RESTful request is a single unicast TCP connection stream. It is routed to exactly one marketplace pod chosen by the kube-proxy random load balancing rule. "
    "The request never broadcasts or multicasts to both pods. Across multiple client requests, incoming traffic is statistically distributed across the two replicas."
)

add_sub_title("4. Service Readiness Probes vs. Direct /healthz Responses (1 point)")
add_para(
    "A successful HTTP 200 or 204 response from a direct curl to '/healthz' does not imply that the marketplace service is ready to process user traffic:"
)
add_bullet(
    "• Architectural Role of readinessProbe:",
    "The readinessProbe in 'k8s/apps.yaml' is an active health probe executed every 5 seconds by the local node kubelet. Only when a Pod passes its readiness probe "
    "does the Kubernetes Endpoints controller register that Pod IP in the Service's active Endpoints / EndpointSlice list. If a pod fails the probe or is in the middle "
    "of startup/shutdown, it is instantly removed from the Endpoints list, preventing kube-proxy from routing user requests to it."
)
add_bullet(
    "• Admission Queue Limiter Bypass in request_limit.go:",
    "Inspection of 'marketplace-service/request_limit.go' reveals that health checks explicitly bypass the request admission limiter:\n"
    "    if r.Method == http.MethodGet && r.URL.Path == \"/healthz\" { next.ServeHTTP(w, r); return }\n"
    "This bypass prevents Kubernetes from mistakenly killing or removing a pod that is experiencing high client traffic. Consequently, if the service is fully saturated "
    "with 8 in-flight requests and 8 queued requests, all subsequent user requests are rejected with HTTP 503 ('marketplace service busy'). Yet, a direct call to "
    "'/healthz' will still return HTTP 200 OK instantly. Thus, a healthy '/healthz' response indicates process liveness, not operational client readiness or capacity."
)

add_sub_title("5. Baseline Transaction Trace and CQRS Response Verification (2 points)")
add_para(
    "Figure 4 confirms the successful deployment of application microservices via 'deploy_apps.sh' and the end-to-end execution of 'run_baseline.sh'."
)

add_image_centered(os.path.join(asset_dir, "sec3_app_deployment_baseline.png"), 6.5,
                   "Figure 4: Deployment of marketplace microservices and successful completion of the end-to-end baseline test.")

add_para(
    "Detailed Transactional Flow through PostgreSQL and Cassandra:"
)
add_bullet(
    "• Step 1: Listing Creation (POST /listings):",
    "Alice lists an item for 25 credits. The marketplace handler executes 'store.CreateListing()', performing an ACID INSERT into the PostgreSQL 'listings' table. "
    "Following the authoritative write, the handler projects the item into Cassandra via 'history.WriteListing()' using QUORUM consistency, inserting rows into "
    "'marketplace_history.listings_by_seller' and 'marketplace_history.available_listings'. The server returns HTTP 201 Created."
)
add_bullet(
    "• Step 2: Order Placement and ACID Settlement (POST /orders):",
    "Bob purchases Alice's listing. In 'store.CreateOrder()', PostgreSQL executes an atomic transactional block: it locks the listing row ('SELECT ... FOR UPDATE') "
    "to guarantee exclusive checkout and prevent double-spending; locks Alice and Bob's account rows; validates that Bob has sufficient balance; debits Bob by 25 credits; "
    "credits Alice by 25 credits; updates listing status to 'sold'; and inserts an immutable record into 'orders'. Upon SQL commit, the handler projects the order to "
    "Cassandra via 'history.WriteOrder()', populating 'purchases_by_buyer' and 'sales_by_seller', updating 'listings_by_seller' to 'sold', and deleting the listing "
    "from 'available_listings'. The baseline confirms that a subsequent attempt to order the same listing fails with HTTP 409 Conflict."
)

add_para("Verified JSON Responses from Baseline Run:")
add_para("Buyer Account Response (GET /accounts/Bob_...):")
add_code_block(
'''{
  "account_id": "Bob_5bfa2638c8af69f7",
  "balance": 75,
  "listings": [],
  "orders": [
    {
      "order_id": "ord-881b2a9e",
      "listing_id": "lst-39ac14df",
      "buyer_id": "Bob_5bfa2638c8af69f7",
      "seller_id": "Alice_5bfa2638c8af69f7",
      "title": "Textbook",
      "credit_cost": 25,
      "status": "completed",
      "listed_at": "2026-11-15T22:18:40Z",
      "ordered_at": "2026-11-15T22:18:42Z",
      "processed_at": "2026-11-15T22:18:42Z"
    }
  ],
  "sales": []
}'''
)

add_para("Seller Account Response (GET /accounts/Alice_...):")
add_code_block(
'''{
  "account_id": "Alice_5bfa2638c8af69f7",
  "balance": 25,
  "listings": [
    {
      "listing_id": "lst-39ac14df",
      "seller_id": "Alice_5bfa2638c8af69f7",
      "title": "Textbook",
      "credit_cost": 25,
      "status": "sold",
      "listed_at": "2026-11-15T22:18:40Z"
    }
  ],
  "orders": [],
  "sales": [
    {
      "order_id": "ord-881b2a9e",
      "listing_id": "lst-39ac14df",
      "buyer_id": "Bob_5bfa2638c8af69f7",
      "seller_id": "Alice_5bfa2638c8af69f7",
      "title": "Textbook",
      "credit_cost": 25,
      "status": "completed",
      "listed_at": "2026-11-15T22:18:40Z",
      "ordered_at": "2026-11-15T22:18:42Z",
      "processed_at": "2026-11-15T22:18:42Z"
    }
  ]
}'''
)

add_para("Public Marketplace Browse Response (GET /listings):")
add_code_block(
'''{
  "listings": []
}'''
)
add_para(
    "The browse response returns an empty listings array ('listings: []') because the purchase transaction successfully executed the projection deletion "
    "statement in Cassandra: 'DELETE FROM marketplace_history.available_listings WHERE feed = 'all' AND listed_at = ? AND listing_id = ?'. This proves "
    "that sold inventory is immediately purged from public feeds while persisting in historical account activity."
)

# ==================== SECTION IV ====================
add_sec_title("Section IV: Retrying Transient Failures and Fault Injection Analysis")

add_sub_title("1. Bounded Retry Implementation in History Service (2 points)")
add_para(
    "To handle transient Cassandra write failures caused by temporary node restarts, network jitter, or JVM garbage collection pauses, the 'write' method "
    "in 'marketplace-service/history/history.go' was enhanced with a bounded retry loop. The implementation inspects errors using 'transientCassandraError()' "
    "and retries up to 's.writeRetries' additional times, pausing for 's.retryInterval' between attempts."
)

add_code_block(
'''func (s *History) write(statement string, values ...any) error {
	var err error
	for attempt := 0; attempt <= s.writeRetries; attempt++ {
		err = s.session.Query(statement, values...).Consistency(s.writeConsistency).Exec()
		if err == nil {
			return nil
		}
		if attempt < s.writeRetries && transientCassandraError(err) {
			time.Sleep(s.retryInterval)
			continue
		}
		return err
	}
	return err
}'''
)

add_para(
    "Algorithmic Approach and Error Discrimination:"
)
add_bullet(
    "• Initial Attempt and Bounded Iterations:",
    "The loop executes the primary CQL query at 'attempt = 0'. If the query succeeds, 'nil' is returned immediately with zero overhead. "
    "The loop permits at most 's.writeRetries' additional attempts (total execution attempts equal 1 + s.writeRetries)."
)
add_bullet(
    "• Transient Error Classification:",
    "If an error occurs, the helper 'transientCassandraError(err)' evaluates whether the failure is recoverable. It matches known transient types: "
    "gocql.ErrTimeoutNoResponse, gocql.ErrTooManyTimeouts, gocql.ErrConnectionClosed, gocql.ErrNoConnections, gocql.ErrNoStreams, gocql.ErrUnavailable, "
    "as well as Cassandra request error codes (ErrCodeUnavailable, ErrCodeOverloaded, ErrCodeBootstrapping, ErrCodeWriteTimeout) and net.Error timeouts. "
    "Non-transient errors (such as syntax errors or schema mismatches) immediately abort and return the error without wasteful retries."
)
add_bullet(
    "• Backoff and Fallback Termination:",
    "For transient errors, the thread sleeps for 's.retryInterval' (default 2 seconds) before re-executing. If all retry attempts are exhausted without success, "
    "the final error is returned to the caller, triggering an error log entry in the marketplace service."
)

add_sub_title("2. Comprehensive Fault Injection Experiments and Quantitative Analysis (6 points)")
add_para(
    "Four fault-injection experiments were conducted using 'run_retry.py' with retry counts of 0, 1, 3, and 5. The workload submits 100 uniquely titled listings "
    "at a constant rate of 10 requests per second. At request 50, the script force-deletes 'cassandra-1' and 'cassandra-2', leaving only 'cassandra-0'. "
    "Because the keyspace uses replication factor 3 and write consistency QUORUM (requiring 2 replica acknowledgments), Cassandra writes fail while the pods "
    "are being recreated by the StatefulSet. Figure 5 presents the empirical execution logs across all four experiments."
)

add_image_centered(os.path.join(asset_dir, "sec4_retry_experiments.png"), 6.5,
                   "Figure 5: Experimental trial outputs across 0, 1, 3, and 5 Cassandra write retries under pod termination fault injection.")

add_para(
    "Table 2 summarizes the quantitative outcomes of the four experimental runs."
)

exp_headers = ["Retry Setting", "Expected Listings", "REST Created (HTTP 201)", "REST Failures (HTTP 503)", "Cassandra Rows", "Read View Consistency"]
exp_widths = [1.1, 1.0, 1.2, 1.2, 1.0, 1.0]
exp_rows = [
    ["0 Retries", "100", "100", "0", "51", "51.0% (Severe shortfall)"],
    ["1 Retry", "100", "97", "3", "58", "59.8% (Minor recovery)"],
    ["3 Retries", "100", "83", "17", "79", "95.2% (Substantial recovery)"],
    ["5 Retries", "100", "72", "28", "72", "100.0% (Perfect consistency)"]
]
t_exp = doc.add_table(rows=1, cols=6)
style_table(t_exp, exp_widths, exp_headers, exp_rows)

add_para(
    "Analysis of How Retries Affect Cassandra Views and RESTful Requests:"
)
add_bullet(
    "• Impact on Cassandra Read Views:",
    "With 0 retries, any listing submitted while Cassandra nodes are recovering fails projection immediately. Only 51 listings reach Cassandra out of 100 created, "
    "leaving a 49-listing shortfall (49% data divergence between PostgreSQL and Cassandra). As retries increase to 3 and 5, requests wait long enough (up to 6s and 10s) "
    "for the replaced Cassandra pods to start, initialize gossip, and join the cluster ring. Consequently, Cassandra matching rows increase from 51 to 72. "
    "At 5 retries, 100% of the listings that were committed in PostgreSQL successfully reached Cassandra (72 rows in Cassandra / 72 created in PostgreSQL)."
)
add_bullet(
    "• Impact on RESTful Requests (Admission Saturation):",
    "While retries restore Cassandra consistency, they degrade RESTful request throughput. In the 0-retry case, handlers fail fast, quickly releasing in-flight slots; "
    "hence, all 100 REST requests succeed (HTTP 201). When retries are set to 5, each in-flight request waiting on Cassandra holds a slot for up to 10 seconds. "
    "Because 'request_limit.go' enforces MARKETPLACE_MAX_INFLIGHT=8, MARKETPLACE_MAX_WAITING=8, and MARKETPLACE_QUEUE_WAIT=2s, the admission queue rapidly fills. "
    "Subsequent client requests cannot acquire a processing slot within 2 seconds and are rejected with HTTP 503 Service Unavailable ('reason=queue_timeout' or 'reason=capacity'). "
    "REST failures increase from 0 at zero retries to 28 at five retries."
)
add_bullet(
    "• Do retries solve issues with transient failures?",
    "Retries provide a partial, conditional solution. They resolve transient failures for admitted requests by bridging temporary backend outages and guaranteeing "
    "eventual CQRS read-view consistency. However, synchronous in-line retries create severe head-of-line blocking and thread exhaustion under concurrency. "
    "In synchronous microservices, retries convert backend database latency into client-facing request rejection (HTTP 503). To fully resolve transient failures without "
    "sacrificing API availability, synchronous retries must be replaced by an asynchronous transactional outbox pattern or message queue (e.g., Kafka/RabbitMQ), "
    "allowing the REST endpoint to commit to PostgreSQL and acknowledge the client immediately while background workers reliably project events into Cassandra."
)

add_sub_title("3. Detailed Log Analysis for the 5-Retry Experiment (2 points)")
add_para(
    "To substantiate the quantitative relationship between failed REST requests and successful Cassandra projections, the marketplace container logs "
    "('out/retry-5-marketplace.log') were analyzed. Figure 6 displays the exact log events captured during the trial."
)

add_image_centered(os.path.join(asset_dir, "sec4_log_analysis_5retries.png"), 6.5,
                   "Figure 6: Log analysis of marketplace microservices during the 5-retry trial, demonstrating exact error and event correlation.")

add_para(
    "Mathematical and Causal Log Event Correlation:"
)
add_bullet(
    "• Correlation to REST Failures (28 Rejections):",
    "Grep analysis of 'out/retry-5-marketplace.log' reveals exactly 28 occurrences of 'event=request_rejected':\n"
    "    $ grep -c 'event=request_rejected' out/retry-5-marketplace.log -> 28\n"
    "The log records demonstrate two distinct failure modes triggered by the admission limiter:\n"
    "  1. 'reason=queue_timeout status=503 path=\"/listings\" queue_wait=2s': Occurs when requests wait in the secondary queue for more than 2 seconds "
    "without an in-flight slot becoming available.\n"
    "  2. 'reason=capacity status=503 path=\"/listings\" max_inflight=8 max_waiting=8': Occurs when both the 8 in-flight execution slots and the 8 waiting queue slots "
    "are completely filled, immediately shedding incoming traffic.\n"
    "These 28 rejections exactly account for the 28 REST failures reported by run_retry.py (100 submitted - 28 rejected = 72 created)."
)
add_bullet(
    "• Correlation to Cassandra Matching Rows (72 Rows):",
    "Grep analysis of projection events confirms zero projection failures and exactly 72 successful projections:\n"
    "    $ grep -c 'event=listing_projection_failed' out/retry-5-marketplace.log -> 0\n"
    "    $ grep -c 'event=listing_projected' out/retry-5-marketplace.log -> 72\n"
    "Because the 5-retry policy allowed admitted requests to pause for up to 10 seconds (5 retries * 2s interval), all 72 admitted requests successfully weathered the "
    "Cassandra pod restart window. Once cassandra-1 and cassandra-2 completed initialization and re-established QUORUM, the retried writes succeeded, producing "
    "'event=listing_projected status=201'. This yields exact mathematical alignment:\n"
    "    Expected Listings (100) = REST Created (72) + REST Failures (28)\n"
    "    Cassandra Matching Rows (72) = REST Created (72) - Projection Failures (0) = 72."
)

# ==================== SUMMARY & CONCLUSION ====================
add_sec_title("Summary and Engineering Conclusion")
add_para(
    "Project 5 successfully demonstrated the container orchestration lifecycle of a cloud-native e-commerce application using Kubernetes. "
    "By transitioning from Docker Compose to Kubernetes StatefulSets and Deployments, the infrastructure achieved automated pod self-healing, "
    "declarative resource isolation via cgroups, and dynamic CoreDNS service discovery. The experimental investigation into transient Cassandra failures "
    "highlighted the critical tension between data consistency and service availability: while bounded retries guarantee eventual read-view convergence, "
    "uncontrolled synchronous retry backoff induces severe head-of-line blocking, requiring strict admission limits and asynchronous message-driven architectures "
    "in production cloud deployments."
)

# ----------------- SAVE & CONVERT -----------------
desktop_docx = "/Users/schoudhry/Desktop/ECE473_Project5_Report_ShashwatChoudhry.docx"
desktop_pages = "/Users/schoudhry/Desktop/ECE473_Project5_Report_ShashwatChoudhry.pages"
desktop_pdf = "/Users/schoudhry/Desktop/ECE473_Project5_Report_ShashwatChoudhry.pdf"

repo_dir = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473"
repo_docx = os.path.join(repo_dir, "ECE473_Project5_Report_ShashwatChoudhry.docx")
repo_pages = os.path.join(repo_dir, "ECE473_Project5_Report_ShashwatChoudhry.pages")
repo_pdf = os.path.join(repo_dir, "ECE473_Project5_Report_ShashwatChoudhry.pdf")

doc.save(desktop_docx)
doc.save(repo_docx)
print(f"Saved DOCX: {desktop_docx}")

# Convert to Apple Pages via AppleScript
applescript_pages = f'''
tell application "Pages"
    activate
    open POSIX file "{desktop_docx}"
    delay 3
    set frontDoc to front document
    save frontDoc in POSIX file "{desktop_pages}"
    delay 1
    save frontDoc in POSIX file "{repo_pages}"
end tell
'''
try:
    res = subprocess.run(["osascript", "-e", applescript_pages], capture_output=True, text=True, timeout=45)
    print("Pages output:", res.stdout, res.stderr)
    print(f"Generated Pages: {desktop_pages}")
except Exception as e:
    print(f"Pages conversion error: {e}")

# Export to PDF via Apple Pages
applescript_pdf = f'''
tell application "Pages"
    activate
    set frontDoc to front document
    export frontDoc to POSIX file "{desktop_pdf}" as PDF
    delay 1
    export frontDoc to POSIX file "{repo_pdf}" as PDF
end tell
'''
try:
    res_pdf = subprocess.run(["osascript", "-e", applescript_pdf], capture_output=True, text=True, timeout=45)
    print("PDF output:", res_pdf.stdout, res_pdf.stderr)
    print(f"Generated PDF: {desktop_pdf}")
except Exception as e:
    print(f"PDF export error: {e}")

print("ECE473 Project 5 Report complete in DOCX, Pages, and PDF formats!")
