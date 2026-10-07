import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.PrintWriter;

public class DecompileAllToFile extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] arguments = getScriptArgs();
        String outputPath = arguments.length > 0 ? arguments[0] : "decompiled.c";
        // "-" means no filter; an empty argument would be dropped by the Windows .bat launcher.
        String nameFilter = arguments.length > 1 && !arguments[1].equals("-") ? arguments[1] : null;
        int timeoutSeconds = arguments.length > 2 ? Integer.parseInt(arguments[2]) : 60;
        DecompInterface decompiler = new DecompInterface();
        try {
            decompiler.openProgram(currentProgram);
            int count = 0;
            try (PrintWriter writer = new PrintWriter(outputPath, "UTF-8")) {
                FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
                for (Function function : functions) {
                    if (nameFilter != null && !function.getName().contains(nameFilter)) {
                        continue;
                    }
                    DecompileResults results = decompiler.decompileFunction(function, timeoutSeconds, monitor);
                    writer.println("// ==== " + function.getName() + " @ " + function.getEntryPoint());
                    if (results.decompileCompleted()) {
                        writer.println(results.getDecompiledFunction().getC());
                    } else {
                        writer.println("// decompile failed: " + results.getErrorMessage());
                    }
                    count++;
                }
            }
            println("DecompileAllToFile wrote " + count + " functions to " + outputPath);
        } finally {
            decompiler.dispose();
        }
    }
}
