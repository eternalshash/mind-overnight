library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity control_unit is
    Port ( opcode   : in  STD_LOGIC_VECTOR(5 downto 0);
           RegDst   : out STD_LOGIC;
           Branch   : out STD_LOGIC;
           MemRead  : out STD_LOGIC;
           MemtoReg : out STD_LOGIC;
           ALUOp    : out STD_LOGIC_VECTOR(1 downto 0);
           MemWrite : out STD_LOGIC;
           ALUSrc   : out STD_LOGIC;
           RegWrite : out STD_LOGIC);
end control_unit;

architecture Behavioral of control_unit is
begin
    process(opcode)
    begin
        -- Default all signals to 0 to prevent latches
        RegDst   <= '0';
        Branch   <= '0';
        MemRead  <= '0';
        MemtoReg <= '0';
        ALUOp    <= "00";
        MemWrite <= '0';
        ALUSrc   <= '0';
        RegWrite <= '0';

        case opcode is
            when "000000" => -- R-Type (ADD, NAND)
                RegDst   <= '1';
                RegWrite <= '1';
                ALUOp    <= "10";
            
            when "100011" => -- LW (Load Word)
                ALUSrc   <= '1';
                MemtoReg <= '1';
                RegWrite <= '1';
                MemRead  <= '1';
                ALUOp    <= "00";
                
            when "101011" => -- SW (Store Word)
                ALUSrc   <= '1';
                MemWrite <= '1';
                ALUOp    <= "00";
                
            when "000100" => -- BNE (Branch Not Equal)
                Branch   <= '1';
                ALUOp    <= "01";
                
            when "001100" => -- ANDI (AND Immediate)
                ALUSrc   <= '1';
                RegWrite <= '1';
                ALUOp    <= "11"; -- Custom ALUOp for immediate logic
                
            when others =>
                -- Do nothing, defaults hold
        end case;
    end process;
end Behavioral;