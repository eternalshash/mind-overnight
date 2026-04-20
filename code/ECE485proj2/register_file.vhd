library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL; -- Needed to convert 5-bit addresses to integers

entity register_file is
    Port ( clk          : in  STD_LOGIC;
           RegWrite     : in  STD_LOGIC;
           read_reg1    : in  STD_LOGIC_VECTOR(4 downto 0);
           read_reg2    : in  STD_LOGIC_VECTOR(4 downto 0);
           write_reg    : in  STD_LOGIC_VECTOR(4 downto 0);
           write_data   : in  STD_LOGIC_VECTOR(31 downto 0);
           read_data1   : out STD_LOGIC_VECTOR(31 downto 0);
           read_data2   : out STD_LOGIC_VECTOR(31 downto 0));
end register_file;

architecture Behavioral of register_file is

    -- Define our custom 2D memory array: 32 rows, each 32 bits wide
    type reg_array is array(0 to 31) of STD_LOGIC_VECTOR(31 downto 0);
    
    -- Instantiate the array and initialize all registers to 0
    signal registers : reg_array := (others => x"00000000");

begin

    -- =========================================================
    -- WRITE PROCESS (Synchronous)
    -- =========================================================
    process(clk)
    begin
        -- Only write on the rising edge of the clock
        if rising_edge(clk) then
            -- Only write if the Control Unit says so, AND ensure we 
            -- NEVER write to Register 0 (the hardwired $zero register)
            if (RegWrite = '1') and (write_reg /= "00000") then
                -- Convert the 5-bit binary address into an integer index to update the array
                registers(to_integer(unsigned(write_reg))) <= write_data;
            end if;
        end if;
    end process;

    -- =========================================================
    -- READ PROCESS (Asynchronous)
    -- =========================================================
    -- These wires continuously output whatever is in the requested register.
    read_data1 <= registers(to_integer(unsigned(read_reg1)));
    read_data2 <= registers(to_integer(unsigned(read_reg2)));

end Behavioral;
