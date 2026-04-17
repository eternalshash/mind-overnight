library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity alu_control_unit is
    Port ( ALUOp       : in  STD_LOGIC_VECTOR(1 downto 0);
           funct       : in  STD_LOGIC_VECTOR(5 downto 0);
           alu_control : out STD_LOGIC_VECTOR(3 downto 0));
end alu_control_unit;

architecture Behavioral of alu_control_unit is
begin
    process(ALUOp, funct)
    begin
        case ALUOp is
            when "00" => alu_control <= "0010"; -- LW/SW (ADD)
            when "01" => alu_control <= "0110"; -- BNE (SUB for comparison)
            when "11" => alu_control <= "0000"; -- ANDI (AND logic)
            when "10" => -- R-type
                case funct is
                    when "100000" => alu_control <= "0010"; -- ADD
                    when "100110" => alu_control <= "1100"; -- NAND
                    when others   => alu_control <= "1111"; -- Error/Unknown
                end case;
            when others => alu_control <= "1111";
        end case;
    end process;
end Behavioral;
