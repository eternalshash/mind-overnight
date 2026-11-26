import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os
import shutil
import subprocess

# ----------------- FILE PATHS -----------------
desktop_docx = "/Users/schoudhry/Desktop/ECE473_Project6_Report_ShashwatChoudhry.docx"
desktop_pages = "/Users/schoudhry/Desktop/ECE473_Project6_Report_ShashwatChoudhry.pages"
desktop_pdf = "/Users/schoudhry/Desktop/ECE473_Project6_Report_ShashwatChoudhry.pdf"

ece_dir = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473"
ece_docx = os.path.join(ece_dir, "ECE473_Project6_Report_ShashwatChoudhry.docx")
ece_pages = os.path.join(ece_dir, "ECE473_Project6_Report_ShashwatChoudhry.pages")
ece_pdf = os.path.join(ece_dir, "ECE473_Project6_Report_ShashwatChoudhry.pdf")

asset_dir = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/prj06_assets"
img_sec2_pods = os.path.join(asset_dir, "sec2_kafka_pods_ready.png")
img_sec2_topic = os.path.join(asset_dir, "sec2_kafka_topic_describe.png")
img_sec3_baseline = os.path.join(asset_dir, "sec3_baseline_execution.png")
img_sec3_consumer = os.path.join(asset_dir, "sec3_kafka_console_consumer.png")
img_sec3_logs = os.path.join(asset_dir, "sec3_services_and_workers_log.png")

# ----------------- STYLING CONSTANTS -----------------
COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_NAVY = RGBColor(0, 31, 63)       # #001F3F Deep Navy Accent
COLOR_SECONDARY = RGBColor(0, 51, 102) # #003366 Secondary Blue
COLOR_MUTED = RGBColor(80, 80, 80)
HEX_NAVY = "001F3F"
HEX_LIGHT_BG = "F4F6F9"
HEX_BORDER = "D0D7DE"
HEX_WHITE = "FFFFFF"

doc = docx.Document()

# 1-inch margins
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
        r1.font.size = Pt(10)
        r1.font.color.rgb = COLOR_NAVY
        r2 = p.add_run(val)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(10)
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
    p.paragraph_format.space_before = Pt(9)
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

def add_image_centered(img_path, width_in=5.8, caption_text=""):
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
        r.font.size = Pt(9)
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
            r.font.size = Pt(8.5)
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

# ==============================================================================
# Document Header Block
# ==============================================================================
add_header("ECE 473 / 573: Cloud Computing and Cloud Native Systems",
           "Project 6 Report: Distributed Message Queues with Apache Kafka")

add_meta([
    ("Student Name", "Shashwat Choudhry"),
    ("Student ID", "A20507277"),
    ("Course", "ECE 473 / 573 Cloud Computing and Cloud Native Systems (Fall 2026)"),
    ("Instructor", "Prof. Jia Wang"),
    ("Due Date", "December 06, 2026 (Sunday, End of Day Chicago Time)")
])

# ==============================================================================
# Section II: Kafka Services (3 Points)
# ==============================================================================
add_sec_title("Section II: Kafka Services & Stateful Infrastructure (3 Points)")

add_sub_title("1. Verification of Kafka Cluster Pods & Supporting StatefulSets (1 Point)")
add_para(
    "In Project 6, our marketplace architecture integrates Apache Kafka 4.4.0 in KRaft (Kafka Raft metadata) "
    "mode as an event streaming backbone between asynchronous REST API services and backend database worker pools. "
    "The Kubernetes cluster is provisioned on kind (Kubernetes in Docker) using one control-plane node and five worker nodes "
    "(ece573-prj06-worker through ece573-prj06-worker5). Stateful infrastructure components are orchestrated using "
    "Kubernetes StatefulSets, ensuring stable persistent network identities and dedicated persistent volume claims (PVCs)."
)
add_para(
    "Figure 1 displays the complete cluster status via 'kubectl get services,statefulsets,pods'. The output confirms that "
    "all three Kafka Pods (kafka-0, kafka-1, kafka-2) are in the Running state with 1/1 containers ready, managed under "
    "the StatefulSet 'kafka' (3/3 ready). PostgreSQL (postgres-0) and Apache Cassandra (cassandra-0) are also healthy and running."
)

add_image_centered(img_sec2_pods, 5.8, "Figure 1: Verification of Kafka 3-Node Cluster, PostgreSQL, and Cassandra StatefulSets")

add_sub_title("2. Kafka Topic 'marketplace.commands' Inspection & Partition Mapping (2 Points)")
add_para(
    "The core messaging topic 'marketplace.commands' is created during cluster bootstrap via create_cluster.sh. "
    "Using kafka-topics.sh executed inside the kafka-0 Pod, we inspect the topic topology, replication configuration, and broker mappings."
)

add_image_centered(img_sec2_topic, 5.8, "Figure 2: Inspection of Kafka Topic 'marketplace.commands' Configuration and Partition Metadata")

add_para("Analysis of Topic Configurations:")
add_bullet("Configs: min.insync.replicas=2:",
           "This parameter establishes the minimum number of in-sync replicas (ISR) that must successfully acknowledge a write request "
           "when a producer publishes messages with RequiredAcks = WaitForAll (acks=all). Because the replication factor is 3, "
           "setting min.insync.replicas=2 guarantees that at least two brokers (the partition leader and one follower) commit the record to "
           "their durable write-ahead log (WAL) before an acknowledgment is returned to the client. This enforces strong zero-data-loss guarantees: "
           "even if any single Kafka broker abruptly crashes, the committed message remains safely replicated and available on the surviving in-sync replica.")

add_bullet("Configs: retention.ms=604800000:",
           "This defines the temporal log retention window for the topic in milliseconds. Calculating 604,800,000 / (1000 * 60 * 60 * 24) = 7.0 days. "
           "Kafka retains all committed command records in its append-only commit logs for seven full days regardless of whether consumer workers "
           "have acknowledged or processed them. This enables complete fault tolerance, replayability, and consumer group checkpoint recovery.")

add_para("Partition to Pod Mapping Table:")
add_para(
    "Per k8s/kafka.yaml, the broker Node IDs are dynamically assigned based on the StatefulSet Pod hostname index: "
    "KAFKA_NODE_ID=$((${HOSTNAME##*-} + 1)). Therefore, Node 1 maps to Pod kafka-0, Node 2 maps to Pod kafka-1, "
    "and Node 3 maps to Pod kafka-2. Table 1 maps each of the 4 partitions to its corresponding Leader, Replicas, and In-Sync Replicas (ISR):"
)

t_mapping = doc.add_table(rows=1, cols=5)
style_table(
    t_mapping,
    [1.0, 1.2, 1.3, 1.4, 1.6],
    ["Partition", "Leader Broker", "Leader Pod", "Assigned Replicas", "In-Sync Replicas (ISR)"],
    [
        ["Partition 0", "Broker 3", "kafka-2", "3, 1, 2 (kafka-2, 0, 1)", "3, 1, 2 (All Healthy)"],
        ["Partition 1", "Broker 1", "kafka-0", "1, 2, 3 (kafka-0, 1, 2)", "1, 2, 3 (All Healthy)"],
        ["Partition 2", "Broker 2", "kafka-1", "2, 3, 1 (kafka-1, 2, 0)", "2, 3, 1 (All Healthy)"],
        ["Partition 3", "Broker 1", "kafka-0", "1, 3, 2 (kafka-0, 2, 1)", "1, 3, 2 (All Healthy)"],
    ]
)


# ==============================================================================
# Section III: Marketplace Commands (11 Points)
# ==============================================================================
add_sec_title("Section III: Marketplace Commands & Asynchronous Processing (11 Points)")

add_sub_title("1. End-to-End Baseline Test Execution (1 Point)")
add_para(
    "The baseline integration script ./run_baseline.sh creates distinct seller and buyer accounts, grants credit balance, "
    "submits a listing command, purchases the item via an order command, verifies read views, and confirms that a duplicate order "
    "for the same listing is safely rejected. Figure 3 demonstrates the complete baseline run passing successfully."
)

add_image_centered(img_sec3_baseline, 5.8, "Figure 3: Successful Deployment and ./run_baseline.sh Execution with Unique Generated Identities")

add_sub_title("2. Comprehensive Trace of Baseline Commands across Kafka, Services, and Workers (9 Points)")
add_para(
    "To trace the lifecycle of commands through the decoupled pipeline, we inspect three independent audit artifacts: "
    "(1) the raw Kafka message dump extracted via kafka-console-consumer.sh (Figure 4), (2) the marketplace-service producer logs, "
    "and (3) the marketplace-worker consumer logs (Figure 5)."
)

add_image_centered(img_sec3_consumer, 5.8, "Figure 4: Kafka Console Consumer Verification of Commands on Topic 'marketplace.commands'")
add_image_centered(img_sec3_logs, 5.8, "Figure 5: Synchronized Marketplace Service (Producer) and Worker (Consumer) Execution Logs")

add_para("Detailed Command Traces:")

add_bullet("Command 1: Item Listing (Alice Lists 'Used textbook'):",
           "• Job ID: 0eee2c19f7c605d9b9ff41e04060ce61\n"
           "• Actor / Seller ID: Alice_bb7cb91bfb8b2e7c\n"
           "• Payload Details: title='Used textbook', credit_cost=25\n"
           "• Client Submission Timestamp: 2026-11-07T19:42:01.450496Z\n"
           "• Kafka Routing: Topic 'marketplace.commands', Partition 1, Offset 0\n"
           "• Service Producer Event: [pod/marketplace-service-867885c6b9-fxkqq] 2026/11/07 19:42:01.458 INFO event=queue_published\n"
           "• Worker Consumer Event: [pod/marketplace-worker-57754b578b-b4mb8] 2026/11/07 19:42:01.464 INFO event=command_processing\n"
           "• Commit & Projection: Worker committed checkpoint next_offset=1 (skipped=false, rejected=false, conflict=false) and executed Cassandra projection.")

add_bullet("Command 2: Item Purchase (Bob Orders 'Used textbook'):",
           "• Job ID: 36c46f43e14b9f4e89744d43a5e1ab3c\n"
           "• Actor / Buyer ID: Bob_bb7cb91bfb8b2e7c\n"
           "• Payload Details: listing_id='listing-1', buyer_id='Bob_bb7cb91bfb8b2e7c'\n"
           "• Client Submission Timestamp: 2026-11-07T19:42:01.516503Z\n"
           "• Kafka Routing: Topic 'marketplace.commands', Partition 1, Offset 1\n"
           "• Service Producer Event: [pod/marketplace-service-867885c6b9-vmlcj] 2026/11/07 19:42:01.523 INFO event=queue_published\n"
           "• Worker Consumer Event: [pod/marketplace-worker-57754b578b-b4mb8] 2026/11/07 19:42:01.528 INFO event=command_processing\n"
           "• Commit & Projection: Worker atomically transferred 25 credits from Bob to Alice, marked listing-1 as 'sold', created order-1, and updated next_offset=2.")

add_bullet("Command 3: Duplicate Purchase Attempt (Bob Repeated Order on 'listing-1'):",
           "• Job ID: 6632d092f5726c3553be4c909de91418\n"
           "• Actor / Buyer ID: Bob_bb7cb91bfb8b2e7c\n"
           "• Payload Details: listing_id='listing-1', buyer_id='Bob_bb7cb91bfb8b2e7c'\n"
           "• Client Submission Timestamp: 2026-11-07T19:42:01.571224Z\n"
           "• Kafka Routing: Topic 'marketplace.commands', Partition 1, Offset 2\n"
           "• Service Producer Event: [pod/marketplace-service-867885c6b9-fxkqq] 2026/11/07 19:42:01.577 INFO event=queue_published\n"
           "• Worker Consumer Event: [pod/marketplace-worker-57754b578b-b4mb8] 2026/11/07 19:42:01.581 INFO event=command_processing\n"
           "• Commit & Rejection: Worker recognized listing-1 is already 'sold'; transaction safely marked job as rejected (rejected=true) without transferring credits, advancing next_offset=3.")

add_para("Queue Latency Estimation:")
add_para(
    "By comparing the timestamp when the marketplace service producer receives acknowledgment from Kafka (queue_published) "
    "to the timestamp when the marketplace worker begins consumption (command_processing), we estimate the queueing transit latency:"
)

t_latency = doc.add_table(rows=1, cols=5)
style_table(
    t_latency,
    [1.2, 1.2, 1.4, 1.4, 1.3],
    ["Operation", "Kind & Job ID", "Kafka Ack Timestamp", "Worker Start Timestamp", "Queue Latency (Δt)"],
    [
        ["Command 1", "listing (0eee...)", "19:42:01.458Z", "19:42:01.464Z", "6 ms (0.006 s)"],
        ["Command 2", "order (36c4...)", "19:42:01.523Z", "19:42:01.528Z", "5 ms (0.005 s)"],
        ["Command 3", "repeat (6632...)", "19:42:01.577Z", "19:42:01.581Z", "4 ms (0.004 s)"],
    ]
)
add_para(
    "The observed queue latencies range between 4 ms and 6 ms. This demonstrates that Kafka introduces negligible overhead "
    "while providing robust decoupling, non-blocking HTTP 202 acceptance, and strict write-ahead log persistence."
)

add_sub_title("3. Partition Assignment to Marketplace Worker Pods (1 Point)")
add_para(
    "In our deployment, two marketplace worker Pods (marketplace-worker-57754b578b-b4mb8 and marketplace-worker-57754b578b-cbqfq) "
    "belong to the single Kafka consumer group 'marketplace-workers'. The topic 'marketplace.commands' contains 4 partitions (0, 1, 2, 3)."
)
add_para(
    "Under the default Kafka consumer group RangeAssignor strategy, partitions are sorted numerically and divided evenly among sorted consumers: "
    "• Worker Pod 1 (b4mb8) is assigned Partitions 0 and 1.\n"
    "• Worker Pod 2 (cbqfq) is assigned Partitions 2 and 3.\n"
    "This assignment is directly proven by the worker startup log entries (Figure 5): Pod b4mb8 logs partition_assigned for partitions 0 and 1, "
    "while Pod cbqfq logs partition_assigned for partitions 2 and 3."
)
add_para(
    "Crucially, for orders, async_handlers.go explicitly designates request.ListingID as the Kafka message key (key = 'listing-1'). "
    "Kafka's hash partitioner computes hash('listing-1') mod 4, deterministically routing both the initial order and the repeat order "
    "to Partition 1. Because Partition 1 is exclusively owned by Worker Pod b4mb8, all order operations on listing-1 are guaranteed "
    "to be processed sequentially by the exact same worker thread, completely eliminating concurrent ordering races."
)


# ==============================================================================
# Section IV: Exploring Future Improvements (6 Points)
# ==============================================================================
add_sec_title("Section IV: Exploring Future Architectural Improvements (6 Points)")

add_sub_title("1. Account Job History via Cassandra Job View Table (2 Points)")
add_para(
    "Current Architecture Limitation: Currently, to check job outcome status (GET /accounts/{id}/jobs/{job_id}), the marketplace service "
    "queries the PostgreSQL database directly against the 'job_outcomes' table. Because client polling scripts (such as wait-job.sh) repeatedly "
    "poll this endpoint until completion, PostgreSQL experiences heavy read amplification. Under high concurrency, polling queries compete for "
    "database connection pools and CPU cycles against critical transactional write operations. Furthermore, the account profile endpoint "
    "(GET /accounts/{account_id}) aggregates balance and listing/order history from Cassandra, but omits recent submitted jobs."
)
add_para(
    "Proposed Cassandra Job View Table Design: We propose introducing a dedicated job history table in Cassandra under the keyspace "
    "'marketplace_history':"
)

add_bullet("Proposed Table Schema:",
           "CREATE TABLE marketplace_history.jobs_by_account (\n"
           "    account_id TEXT,\n"
           "    submitted_at TIMESTAMP,\n"
           "    job_id TEXT,\n"
           "    kind TEXT,\n"
           "    status TEXT,\n"
           "    result TEXT,\n"
           "    error_code TEXT,\n"
           "    PRIMARY KEY ((account_id), submitted_at, job_id)\n"
           ") WITH CLUSTERING ORDER BY (submitted_at DESC, job_id ASC);")

add_bullet("Partition Key ((account_id)):",
           "The single partition key is account_id. In Cassandra, the partition key determines hash-ring token placement. "
           "Placing all jobs associated with a single user account onto the same replica node enables single-partition range queries. "
           "This completely avoids costly distributed cross-node scatter-gather scans.")

add_bullet("Clustering Key (submitted_at DESC, job_id ASC):",
           "The clustering columns determine the on-disk sorted order of rows within each account partition. Sorting by submitted_at DESC "
           "stores records in reverse chronological order. This enables instantaneous constant-time retrieval of the user's N most recent jobs "
           "(e.g., 'SELECT * FROM jobs_by_account WHERE account_id = ? LIMIT 10') to enrich the GET /accounts/{id} response. "
           "Appended job_id ASC guarantees primary key uniqueness even if multiple jobs are submitted within the identical millisecond.")

add_bullet("Workload Offloading:",
           "When a worker commits a job in PostgreSQL, it asynchronously writes the outcome into jobs_by_account in Cassandra. "
           "Marketplace API services can then serve all job polling and account history requests directly from Cassandra, completely isolating "
           "PostgreSQL from read polling load and reserving relational capacity strictly for ACID business transactions.")

add_sub_title("2. Bounded Retries Analysis: Kafka Publishing vs. Cassandra Projections (2 Points)")
add_para(
    "In distributed systems, adding retries mitigates transient network blips and failover hiccups, but introduces severe operational "
    "trade-offs depending on where the retry policy is enforced:"
)

add_bullet("Location A: Marketplace Service Publishing to Kafka:",
           "• Failure Nature: Transient broker disconnection, Kafka controller election, or leader metadata refresh.\n"
           "• Impact of Increasing Retries: Sarama's producer currently configures Retry.Max = 5 and Idempotent = true. "
           "Increasing the retry count allows the service to absorb longer broker failovers without immediately failing client requests. "
           "However, because the HTTP handler executes a synchronous wait on queue.Publish(), increasing retries causes client HTTP requests "
           "to block. Under sustained ingress, incoming requests accumulate, exhausting web server goroutines, socket file descriptors, "
           "and memory buffers. If retries time out after an extended period, clients receive 504 Gateway Timeout or 503 Service Unavailable. "
           "Because Idempotent producer is enabled, retried packets within an active TCP session do not produce duplicate Kafka records; "
           "nevertheless, unbounded retries risk cascade server exhaustion.")

add_bullet("Location B: Marketplace Worker Updating Cassandra Read Views:",
           "• Failure Nature: Cassandra node unavailability, GC pause, or write timeout during projection.\n"
           "• Impact of Increasing Retries: In the worker consumerHandler (consumer.go), ConsumeClaim processes assigned partition messages "
           "in strict linear offset order. If the worker blocks in a retry loop attempting to write to Cassandra, it introduces catastrophic "
           "Head-of-Line (HoL) Blocking: no subsequent messages in that Kafka partition can be processed! Partition throughput drops to zero, "
           "causing consumer lag to spike and delaying unrelated user transactions. "
           "Conversely, the current implementation attempts projection only once and logs an error upon failure, which risks permanent read-view drift. "
           "The architectural solution is to limit worker inline retries to 2 or 3 short attempts, and if failures persist, route the projection event "
           "to a Dead-Letter Queue (DLQ) or background asynchronous reconciler, allowing the main Kafka consumer loop to advance without delay.")

add_sub_title("3. Idempotent Ordering Design & Architectural Placement (2 Points)")
add_para(
    "Scenario Analysis: A buyer submits an order for listing-1. The marketplace service publishes command job-1 to Kafka and returns HTTP 202, "
    "but the client drops the TCP connection before receiving the response. Believing the order failed, the buyer resubmits. "
    "The service treats this as a new request, assigns job-2, and publishes it to Kafka. Worker 1 processes job-1, deducts 25 credits, "
    "marks listing-1 as 'sold', and creates order-1. Subsequently, worker 2 processes job-2, sees that listing-1 is already sold, "
    "and rejects job-2. The buyer is confused and lacks access to order-1."
)

add_bullet("Feasibility of Duplicate Recognition:",
           "Yes, the architecture can be extended to recognize repeat purchases by the same buyer, returning the existing order ID "
           "without charging credits twice.")

add_bullet("Where Must This Decision Be Made?",
           "This decision MUST be made inside the PostgreSQL database transaction executed by the marketplace worker (orders.go / createOrderTx), "
           "NOT at the stateless marketplace service layer.\n"
           "Why? At the API layer, Kafka messages are merely queued asynchronously; the API cannot know whether an earlier queued order will "
           "succeed, fail, or be delayed. Checking at the API layer creates severe race conditions when duplicate requests hit different Pods. "
           "In contrast, the worker executes within a Serializable transaction on PostgreSQL with row-level locks on 'listings' and 'orders'.")

add_bullet("Idempotent Implementation Mechanism:",
           "1. The client supplies a deterministic idempotency token (e.g., Idempotency-Key header or hash(buyer_id, listing_id)).\n"
           "2. Inside createOrderTx in PostgreSQL, the worker queries existing orders: "
           "'SELECT order_id, buyer_id, status FROM orders WHERE listing_id = $1'.\n"
           "3. Handling Same Buyer: If an order already exists and order.buyer_id == command.buyer_id, the worker detects a duplicate submission. "
           "It skips credit deduction, leaves listing status as 'sold', and records job_outcomes for job-2 as 'completed' with the original order_id.\n"
           "4. Handling Different Buyer: If an order exists but order.buyer_id != command.buyer_id, another buyer legitimately acquired the item first. "
           "The transaction rejects the request with 'listing is no longer available'. No credits are deducted.\n"
           "5. Crash Recovery: Because the idempotency verification and consumer_offsets increment execute within the identical atomic database transaction, "
           "worker crashes or partition rebalances replay offsets without risk of double-charging.")

# Save DOCX
doc.save(desktop_docx)
print("Saved DOCX to:", desktop_docx)
shutil.copyfile(desktop_docx, ece_docx)
print("Copied DOCX to:", ece_docx)

# Convert to Apple Pages and PDF via AppleScript
applescript = f'''
tell application "Pages"
    activate
    delay 1
    close every document saving no
    delay 1
    set theDoc to open POSIX file "{desktop_docx}"
    delay 2
    save theDoc in POSIX file "{desktop_pages}"
    delay 1
    export theDoc to POSIX file "{desktop_pdf}" as PDF
    delay 1
    close theDoc saving no
    delay 1
    open POSIX file "{desktop_pages}"
    activate
end tell
'''

print("Running AppleScript to convert DOCX to Pages and PDF...")
res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
print("AppleScript stdout:", res.stdout)
print("AppleScript stderr:", res.stderr)

# Copy Pages and PDF to course folder
if os.path.exists(desktop_pages):
    if os.path.isdir(desktop_pages):
        shutil.copytree(desktop_pages, ece_pages, dirs_exist_ok=True)
    else:
        shutil.copy2(desktop_pages, ece_pages)
    print("Copied Pages to:", ece_pages)

if os.path.exists(desktop_pdf):
    shutil.copy2(desktop_pdf, ece_pdf)
    print("Copied PDF to:", ece_pdf)

print("Project 6 report generation complete!")
