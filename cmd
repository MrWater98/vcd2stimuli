yosys RocketTile.ys  > btor.log 2>&1
../../ponocca/build/pono --promote-inputvars --bound 500 -p 0 -e bmc --vcd cex.vcd -v 3 RocketTile_dut.btor 