library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity mips_single_cycle is
    Port ( clk   : in STD_LOGIC;
           reset : in STD_LOGIC);
end mips_single_cycle;

architecture Structural of mips_single_cycle is

    component pc_register
        Port ( clk    : in  STD_LOGIC; reset  : in  STD_LOGIC;
               pc_in  : in  STD_LOGIC_VECTOR(31 downto 0); pc_out : out STD_LOGIC_VECTOR(31 downto 0));
    end component;

    component instruction_memory
        Port ( read_addr : in  STD_LOGIC_VECTOR(31 downto 0); instr     : out STD_LOGIC_VECTOR(31 downto 0));
    end component;

    component control_unit
        Port ( opcode   : in  STD_LOGIC_VECTOR(5 downto 0); RegDst   : out STD_LOGIC;
               Branch   : out STD_LOGIC; MemRead  : out STD_LOGIC; MemtoReg : out STD_LOGIC;
               ALUOp    : out STD_LOGIC_VECTOR(1 downto 0); MemWrite : out STD_LOGIC;
               ALUSrc   : out STD_LOGIC; RegWrite : out STD_LOGIC);
    end component;

    component alu_control_unit
        Port ( ALUOp       : in  STD_LOGIC_VECTOR(1 downto 0); funct       : in  STD_LOGIC_VECTOR(5 downto 0);
               alu_control : out STD_LOGIC_VECTOR(3 downto 0));
    end component;

    component register_file
        Port ( clk        : in  STD_LOGIC; RegWrite   : in  STD_LOGIC;
               read_reg1  : in  STD_LOGIC_VECTOR(4 downto 0); read_reg2  : in  STD_LOGIC_VECTOR(4 downto 0);
               write_reg  : in  STD_LOGIC_VECTOR(4 downto 0); write_data : in  STD_LOGIC_VECTOR(31 downto 0);
               read_data1 : out STD_LOGIC_VECTOR(31 downto 0); read_data2 : out STD_LOGIC_VECTOR(31 downto 0));
    end component;

    component alu_32bit
        Port ( a           : in  STD_LOGIC_VECTOR(31 downto 0); b           : in  STD_LOGIC_VECTOR(31 downto 0);
               alu_control : in  STD_LOGIC_VECTOR(3 downto 0); alu_result  : out STD_LOGIC_VECTOR(31 downto 0);
               zero_flag   : out STD_LOGIC);
    end component;

    component data_memory
        Port ( clk        : in  STD_LOGIC; mem_write  : in  STD_LOGIC; mem_read   : in  STD_LOGIC;
               addr       : in  STD_LOGIC_VECTOR(31 downto 0); write_data : in  STD_LOGIC_VECTOR(31 downto 0);
               read_data  : out STD_LOGIC_VECTOR(31 downto 0));
    end component;

    -- Signals
    signal current_pc, next_pc, pc_plus_4, branch_target : STD_LOGIC_VECTOR(31 downto 0);
    signal instruction : STD_LOGIC_VECTOR(31 downto 0);
    signal sig_RegDst, sig_Branch, sig_MemRead, sig_MemtoReg : STD_LOGIC;
    signal sig_MemWrite, sig_ALUSrc, sig_RegWrite, sig_zero_flag : STD_LOGIC;
    signal sig_ALUOp : STD_LOGIC_VECTOR(1 downto 0);
    signal sig_alu_ctrl_wire : STD_LOGIC_VECTOR(3 downto 0);
    signal reg_read_data1, reg_read_data2, alu_main_result, mem_read_data : STD_LOGIC_VECTOR(31 downto 0);
    signal write_reg_mux_out : STD_LOGIC_VECTOR(4 downto 0);
    signal alu_b_input, write_back_mux_out, sign_ext_imm : STD_LOGIC_VECTOR(31 downto 0);
    signal pc_src : STD_LOGIC;

begin
    -- ==================== COMBINATIONAL LOGIC ====================
    pc_plus_4 <= std_logic_vector(unsigned(current_pc) + 4);

    -- Sign Extension
    sign_ext_imm <= x"FFFF" & instruction(15 downto 0) when instruction(15) = '1' else x"0000" & instruction(15 downto 0);

    -- Branch Target Address Calculation (PC+4 + Immediate*4)
    branch_target <= std_logic_vector(unsigned(pc_plus_4) + unsigned(sign_ext_imm(29 downto 0) & "00"));

    -- BNE Branch Logic: Branch if Branch signal is HIGH and Zero Flag is LOW
    pc_src <= sig_Branch and (not sig_zero_flag);

    -- PC Source Mux
    next_pc <= branch_target when pc_src = '1' else pc_plus_4;

    -- Data Muxes
    write_reg_mux_out <= instruction(15 downto 11) when sig_RegDst = '1' else instruction(20 downto 16);
    alu_b_input <= sign_ext_imm when sig_ALUSrc = '1' else reg_read_data2;
    write_back_mux_out <= mem_read_data when sig_MemtoReg = '1' else alu_main_result;

    -- ==================== COMPONENT INSTANTIATIONS ====================
    PC_INST: pc_register port map (clk => clk, reset => reset, pc_in => next_pc, pc_out => current_pc);
    IMEM_INST: instruction_memory port map (read_addr => current_pc, instr => instruction);
    CTRL_INST: control_unit port map (opcode => instruction(31 downto 26), RegDst => sig_RegDst, Branch => sig_Branch, MemRead => sig_MemRead, MemtoReg => sig_MemtoReg, ALUOp => sig_ALUOp, MemWrite => sig_MemWrite, ALUSrc => sig_ALUSrc, RegWrite => sig_RegWrite);
    ALU_CTRL_INST: alu_control_unit port map (ALUOp => sig_ALUOp, funct => instruction(5 downto 0), alu_control => sig_alu_ctrl_wire);
    REG_FILE_INST: register_file port map (clk => clk, RegWrite => sig_RegWrite, read_reg1 => instruction(25 downto 21), read_reg2 => instruction(20 downto 16), write_reg => write_reg_mux_out, write_data => write_back_mux_out, read_data1 => reg_read_data1, read_data2 => reg_read_data2);
    
    ALU_INST: alu_32bit port map (
        a => reg_read_data1, 
        b => alu_b_input, 
        alu_control => sig_alu_ctrl_wire, 
        alu_result => alu_main_result, 
        zero_flag => sig_zero_flag  -- Linked to BNE logic
    );

    DMEM_INST: data_memory port map (clk => clk, mem_write => sig_MemWrite, mem_read => sig_MemRead, addr => alu_main_result, write_data => reg_read_data2, read_data => mem_read_data);

end Structural;