import PriceProvider from "@/components/PriceProvider";
import Workstation from "@/components/Workstation";

export default function Home() {
  return (
    <PriceProvider>
      <Workstation />
    </PriceProvider>
  );
}
