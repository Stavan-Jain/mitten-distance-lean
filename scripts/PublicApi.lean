import MittenDistance.M150.Distance
import MittenDistance.M150.Logicals
import QEC.Stabilizer.Framework.Core.CodeNotation

open Quantum.StabilizerGroup
open scoped Quantum.StabilizerGroup
open Quantum.Stabilizer.Homological.LP.M150

#check (mitten150StabilizerCodeWithDistance : Code[[150, 30, 10]])
#check (m150StabilizerCodeWithLogicals : StabilizerCodeWithLogicals 150 30)
#check (m150StabilizerCode_hasCodeDistance_10 : HasCodeDistance m150StabilizerCode 10)

namespace MittenDistance.PublicApi

/-- Both public packages refer to the same canonical stabilizer code. -/
theorem distance_logicals_same_code :
    mitten150StabilizerCodeWithDistance.toStabilizerCode =
      m150StabilizerCodeWithLogicals.toStabilizerCode := rfl

end MittenDistance.PublicApi

#print axioms floorX
#print axioms floorZ
#print axioms m150StabilizerCode_hasCodeDistance_10
#print axioms mitten150StabilizerCodeWithDistance
#print axioms m150StabilizerCodeWithLogicals
