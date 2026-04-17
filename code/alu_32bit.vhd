library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity alu_32bit is
    Port ( a           : in  STD_LOGIC_VECTOR(31 downto 0);
           b           : in  STD_LOGIC_VECTOR(31 downto 0);
           alu_control : in  STD_LOGIC_VECTOR(3 downto 0);
           alu_result  : out STD_LOGIC_VECTOR(31 downto 0);
           zero_flag   : out STD_LOGIC);
end alu_32bit;

architecture Behavioral of alu_32bit is
    signal internal_result : STD_LOGIC_VECTOR(31 downto 0);
begin
    process(a, b, alu_control)
    begin
        case alu_control is
            when "0000" => -- AND
                internal_result <= a and b;
            when "0001" => -- OR
                internal_result <= a or b;
            when "0010" => -- ADD
                internal_result <= std_logic_vector(signed(a) + signed(b));
            when "0110" => -- SUBTRACT
                internal_result <= std_logic_vector(signed(a) - signed(b));
            when "1100" => -- NAND
                internal_result <= a nand b;
            when others =>
                internal_result <= (others => '0');
        end case;
    end process;

    alu_result <= internal_result;
    
    -- Zero flag logic: 1 if result is 0, otherwise 0
    zero_flag <= '1' when internal_result = x"00000000" else '0';

end Behavioral;