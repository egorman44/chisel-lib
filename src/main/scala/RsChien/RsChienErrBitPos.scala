package Rs

import chisel3._
import chisel3.util._
/////////////////////////////////////////
// RsChienErrBitPos 
/////////////////////////////////////////

class RsChienErrBitPos extends Module with GfParams {
  val io = IO(new Bundle {
    val errLocatorIf = Input(Valid(new ErrLocatorBundle()))
    val bitPos = Output(new BitPosIf)
  })
  // Localparams
  val rootsNum = symbNum - 1
  val numOfCycles = math.ceil(rootsNum/chienRootsPerCycle.toDouble).toInt
  val chienNonValid = ((1 << (rootsNum % chienRootsPerCycle)) -1)

  val polyEval = for(i <- 0 until chienRootsPerCycle) yield Module(new GfPolyEvalHorner(tLen+1, ffStepPolyEval))
  val roots = Wire(Valid(Vec(chienRootsPerCycle, UInt(symbWidth.W))))
  
  if(numOfCycles == 1) {
    for(i <- 0 until chienRootsPerCycle) {
      roots.bits := i.U
    }
    roots.valid := io.errLocatorIf.valid
  } else {

    val cntrUpLimit = (numOfCycles-1)*chienRootsPerCycle
    val cntr = RegInit(UInt(log2Ceil(rootsNum).W), 0.U)

    when(io.errLocatorIf.valid === 1.U) {
      cntr := chienRootsPerCycle.U
    }.elsewhen(cntr =/= 0.U) {
      when(cntr =/= (cntrUpLimit).U) {
        cntr := cntr + chienRootsPerCycle.U
      }.otherwise {
        cntr := 0.U
      }
    }

    for(i <- 0 until chienRootsPerCycle) {
      roots.bits(i) := alphaToSymb(cntr + i.U)
    }
    roots.valid := io.errLocatorIf.valid | (cntr =/= 0.U)
  }

  // Generate Sel  
  val ffs = Module(new FindFirstSet(tLen+1))
  val errLocatorSel = io.errLocatorIf.bits.errLocatorSel
  ffs.io.in := errLocatorSel
  val errLocatorFfs = ffs.io.out

  for(i <- 0 until chienRootsPerCycle) {
    polyEval(i).io.coefVec.bits.data := io.errLocatorIf.bits.errLocator
    polyEval(i).io.coefVec.bits.sel := errLocatorFfs
    polyEval(i).io.coefVec.valid := roots.valid
    polyEval(i).io.x := roots.bits(i)
  }

  val errVal = VecInit(polyEval.map(_.io.evalValue.bits))
  dontTouch(errVal)
  // Capture EvalVal into register
  val bitPos = Reg(Vec(chienRootsPerCycle, Bool() ))
  bitPos := errVal.map(x => ~x.orR)

  // We can use any Valid here, so take (0)
  val bitPosVld = polyEval(0).io.evalValue.valid
  dontTouch(bitPosVld)
  val bitPosVldQ = RegNext(next=bitPosVld, init=false.B)

  val lastCycle = Wire(Bool())
  when(bitPosVld === 0.U & bitPosVldQ === 1.U){
    lastCycle := 1.U
    io.bitPos.last := 1.U
  }.otherwise{
    lastCycle := 0.U
    io.bitPos.last := 0.U
  }

  io.bitPos.valid := bitPosVldQ

  when(lastCycle & chienNonValid.U =/= 0.U) {
    // Nulify bits that is not valid.
    io.bitPos.pos := bitPos.asTypeOf(UInt(chienRootsPerCycle.W)) & chienNonValid.U
  }.otherwise{
    io.bitPos.pos := bitPos.asTypeOf(UInt(chienRootsPerCycle.W))
  }
  
}
