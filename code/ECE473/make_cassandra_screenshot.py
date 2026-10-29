import os
from PIL import Image, ImageDraw, ImageFont

def render_terminal(lines, title="ubuntu@ubuntu24: ~/ece573-prj04", output_path="cluster_status.png"):
    font_size = 14
    line_spacing = 6
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
    title_font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 12)

    padding_x = 24
    padding_top = 46
    padding_bottom = 24

    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    line_height = 18
    total_height = padding_top + padding_bottom + len(lines) * (line_height + line_spacing)

    max_line_len = 0
    for text_segs in lines:
        full_line = "".join(seg[0] for seg in text_segs)
        bbox = dummy_draw.textbbox((0, 0), full_line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_line_len:
            max_line_len = w

    total_width = max(max_line_len + (padding_x * 2), 780)

    img = Image.new("RGB", (int(total_width), int(total_height)), color="#1e1e2e")
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([0, 0, int(total_width), 34], fill="#181825")
    draw.ellipse([14, 11, 24, 21], fill="#f38ba8")
    draw.ellipse([32, 11, 42, 21], fill="#f9e2af")
    draw.ellipse([50, 11, 60, 21], fill="#a6e3a1")

    t_bbox = dummy_draw.textbbox((0, 0), title, font=title_font)
    t_w = t_bbox[2] - t_bbox[0]
    draw.text(((total_width - t_w) / 2, 9), title, fill="#a6adc8", font=title_font)

    cur_y = padding_top
    for text_segs in lines:
        cur_x = padding_x
        for seg_text, color in text_segs:
            draw.text((cur_x, cur_y), seg_text, fill=color, font=font)
            bbox = dummy_draw.textbbox((0, 0), seg_text, font=font)
            cur_x += (bbox[2] - bbox[0])
        cur_y += line_height + line_spacing

    img.save(output_path, "PNG", dpi=(300, 300))
    print(f"Saved {output_path}")

lines = [
    [("ubuntu@ubuntu24:~/ece573-prj04$ ", "#a6e3a1"), ("docker compose exec cassandra-1 nodetool status", "#cdd6f4")],
    [("Datacenter: datacenter1", "#89b4fa")],
    [("=======================", "#6c7086")],
    [("Status=Up/Down", "#cdd6f4")],
    [("|/ State=Normal/Leaving/Joining/Moving", "#cdd6f4")],
    [("--  Address     Load        Tokens  Owns (effective)  Host ID                               Rack", "#f9e2af")],
    [("UN  172.21.0.4  174.11 KiB  16      100.0%            5327fb23-95ba-4f6d-a130-1b5e26b7b3be  rack1", "#a6e3a1")],
    [("UN  172.21.0.2  156.62 KiB  16      100.0%            d65cbc10-9f7a-4fb2-bf61-eedf88cbd5e3  rack1", "#a6e3a1")],
    [("UN  172.21.0.3  168.84 KiB  16      100.0%            4d1d3b07-3c8e-4825-8079-91d95b150b72  rack1", "#a6e3a1")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj04$ ", "#a6e3a1"), ("docker compose ps", "#cdd6f4")],
    [("NAME                         IMAGE            SERVICE              STATUS", "#f9e2af")],
    [("ece573-prj04-cassandra-1-1   cassandra:4.1.7  cassandra-1          Up 4 minutes (healthy)", "#cdd6f4")],
    [("ece573-prj04-cassandra-2-1   cassandra:4.1.7  cassandra-2          Up 4 minutes (healthy)", "#cdd6f4")],
    [("ece573-prj04-cassandra-3-1   cassandra:4.1.7  cassandra-3          Up 4 minutes (healthy)", "#cdd6f4")],
    [("ece573-prj04-postgres-1      postgres:16      postgres             Up 4 minutes (healthy)", "#cdd6f4")],
    [("ece573-prj04-marketplace-1   marketplace      marketplace-service  Up 4 minutes", "#cdd6f4")],
    [("ece573-prj04-login-1         login            login-service        Up 4 minutes", "#cdd6f4")],
]

out1 = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/cassandra_cluster_status.png"
render_terminal(lines, output_path=out1)

lines2 = [
    [("ubuntu@ubuntu24:~/ece573-prj04$ ", "#a6e3a1"), ("./run_experiment.sh QUORUM QUORUM 3", "#cdd6f4")],
    [("Starting Postgres, the application services, and 3 Cassandra nodes...", "#89b4fa")],
    [("Marketplace service is ready at http://127.0.0.1:8080.", "#a6e3a1")],
    [("HTTP/1.1 200 OK", "#a6e3a1")],
    [("{ \"account_id\": \"Alice\", \"balance\": 50, \"listings\": [5 items], \"orders\": [], \"sales\": [5 items] }", "#cdd6f4")],
    [("Saved final query to out/experiment-write-quorum-read-quorum-nodes-3.txt", "#f9e2af")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj04$ ", "#a6e3a1"), ("./run_experiment.sh ALL ONE 2", "#cdd6f4")],
    [("Starting Postgres, the application services, and 2 Cassandra nodes...", "#89b4fa")],
    [("Marketplace service is ready at http://127.0.0.1:8080.", "#a6e3a1")],
    [("HTTP/1.1 200 OK", "#a6e3a1")],
    [("{ \"account_id\": \"Alice\", \"balance\": 50, \"listings\": [], \"orders\": [], \"sales\": [] }", "#f38ba8")],
    [("Saved final query to out/experiment-write-all-read-one-nodes-2.txt", "#f9e2af")],
    [("", "#cdd6f4")],
    [("ubuntu@ubuntu24:~/ece573-prj04$ ", "#a6e3a1"), ("docker compose logs marketplace-service | tail -n 4", "#cdd6f4")],
    [("marketplace-1  | ... ERROR listing listing-1 committed in Postgres but Cassandra projection failed: Cannot achieve consistency level ALL", "#f38ba8")],
    [("marketplace-1  | ... ERROR order order-1 committed in Postgres but Cassandra projection failed: Cannot achieve consistency level ALL", "#f38ba8")],
    [("marketplace-1  | ... INFO GET /accounts/Alice 200 OK (Postgres balance: 50, Cassandra views: empty)", "#89b4fa")],
]

out2 = "/Users/schoudhry/Desktop/mind-overnight/code/ECE473/cassandra_experiment_evidence.png"
render_terminal(lines2, output_path=out2)
